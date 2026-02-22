"""
Marker-missing detector.

Tracks whether expected marker events (e.g. DRUG_ON) have arrived
within the planned session window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarkerMissingDetector:
    expected_markers: list[str] = field(default_factory=lambda: ["DRUG_ON"])
    deadline_seconds: float = 300.0  # after session start
    fps: float = 30.0

    _received: set[str] = field(default_factory=set, init=False)
    _session_start_frame: int = field(default=0, init=False)

    def mark_received(self, marker_type: str) -> None:
        self._received.add(marker_type)

    def set_session_start(self, frame_index: int = 0) -> None:
        self._session_start_frame = frame_index

    def evaluate(self, current_frame: int) -> list[dict[str, Any]]:
        """Return list of MARKER_MISSING findings for each overdue marker."""
        elapsed_s = (current_frame - self._session_start_frame) / self.fps
        if elapsed_s < self.deadline_seconds:
            return []

        findings = []
        for marker in self.expected_markers:
            if marker not in self._received:
                findings.append(
                    {
                        "type": "MARKER_MISSING",
                        "confidence": 0.95,
                        "summary": (
                            f"Expected marker {marker!r} was not received within "
                            f"{self.deadline_seconds}s of session start"
                        ),
                        "evidence": {
                            "frame_start": self._session_start_frame,
                            "frame_end": current_frame,
                            "metric_trace_ids": [],
                        },
                    }
                )
        return findings
