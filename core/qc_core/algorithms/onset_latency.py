"""
Onset latency detector.

After a DRUG_ON marker, monitors the per-frame ROI mean for a statistically
significant change-point.  Reports FLOW_DELAY if onset does not occur within
the expected window [expected_onset_min_s, expected_onset_max_s].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class OnsetLatencyDetector:
    fps: float = 30.0
    expected_onset_min_s: float = 5.0
    expected_onset_max_s: float = 60.0
    change_threshold_sigma: float = 3.0  # std deviations above baseline

    _baseline_samples: list[float] = field(default_factory=list, init=False)
    _post_drug_samples: list[float] = field(default_factory=list, init=False)
    _drug_on_frame: int | None = field(default=None, init=False)
    _onset_detected_frame: int | None = field(default=None, init=False)
    _baseline_mean: float = field(default=0.0, init=False)
    _baseline_std: float = field(default=1.0, init=False)

    def set_baseline(self, samples: list[float]) -> None:
        self._baseline_samples = list(samples)
        arr = np.asarray(samples, dtype=float)
        self._baseline_mean = float(np.mean(arr))
        self._baseline_std = max(float(np.std(arr)), 1e-8)

    def drug_on(self, frame_index: int) -> None:
        self._drug_on_frame = frame_index
        self._post_drug_samples = []
        self._onset_detected_frame = None

    def update(self, frame_mean: float, frame_index: int) -> None:
        if self._drug_on_frame is None:
            self._baseline_samples.append(frame_mean)
            if len(self._baseline_samples) > int(self.fps * 30):
                self._baseline_samples.pop(0)
            arr = np.asarray(self._baseline_samples, dtype=float)
            self._baseline_mean = float(np.mean(arr))
            self._baseline_std = max(float(np.std(arr)), 1e-8)
        else:
            if self._onset_detected_frame is None:
                self._post_drug_samples.append(frame_mean)
                z = (frame_mean - self._baseline_mean) / self._baseline_std
                if abs(z) >= self.change_threshold_sigma:
                    self._onset_detected_frame = frame_index

    def evaluate(self, current_frame: int) -> dict[str, Any] | None:
        if self._drug_on_frame is None:
            return None

        elapsed_s = (current_frame - self._drug_on_frame) / self.fps

        if self._onset_detected_frame is not None:
            latency_s = (self._onset_detected_frame - self._drug_on_frame) / self.fps
            if latency_s > self.expected_onset_max_s:
                confidence = min(1.0, (latency_s - self.expected_onset_max_s) / self.expected_onset_max_s)
                return {
                    "type": "FLOW_DELAY",
                    "confidence": round(confidence, 3),
                    "summary": (
                        f"Drug onset detected at {latency_s:.1f}s after DRUG_ON "
                        f"(expected ≤ {self.expected_onset_max_s}s). "
                        "Check bubble/flow path."
                    ),
                    "evidence": {
                        "frame_start": self._drug_on_frame,
                        "frame_end": self._onset_detected_frame,
                        "metric_trace_ids": ["onset_latency_s"],
                    },
                }
            return None

        # No onset yet – check if we've exceeded the max window
        if elapsed_s > self.expected_onset_max_s:
            confidence = min(1.0, (elapsed_s - self.expected_onset_max_s) / self.expected_onset_max_s)
            return {
                "type": "FLOW_DELAY",
                "confidence": round(confidence, 3),
                "summary": (
                    f"No drug onset detected after {elapsed_s:.1f}s "
                    f"(expected ≤ {self.expected_onset_max_s}s). "
                    "Check bubble/flow path."
                ),
                "evidence": {
                    "frame_start": self._drug_on_frame,
                    "frame_end": current_frame,
                    "metric_trace_ids": ["onset_latency_s"],
                },
            }
        return None
