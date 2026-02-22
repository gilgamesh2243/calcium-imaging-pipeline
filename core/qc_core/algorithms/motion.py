"""
Motion / drift detector using phase-correlation between consecutive frames.

Accumulates per-frame translation vectors and triggers MOTION finding
when the cumulative drift exceeds a threshold.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np


def _phase_correlation_shift(ref: np.ndarray, target: np.ndarray) -> tuple[float, float]:
    """Compute (dy, dx) translation via phase correlation."""
    # Work in float32 for speed
    r = ref.astype(np.float32)
    t = target.astype(np.float32)
    R = np.fft.fft2(r)
    T = np.fft.fft2(t)
    cross = R * np.conj(T)
    denom = np.abs(cross) + 1e-8
    norm = cross / denom
    corr = np.abs(np.fft.ifft2(norm))
    idx = np.unravel_index(np.argmax(corr), corr.shape)
    dy = idx[0] if idx[0] < r.shape[0] // 2 else idx[0] - r.shape[0]
    dx = idx[1] if idx[1] < r.shape[1] // 2 else idx[1] - r.shape[1]
    return float(dy), float(dx)


@dataclass
class MotionDetector:
    max_drift_px: float = 10.0       # cumulative drift threshold in pixels
    window_frames: int = 100         # rolling window for drift accumulation

    _prev_frame: np.ndarray | None = field(default=None, init=False, repr=False)
    _shifts: deque = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        self._shifts = deque(maxlen=self.window_frames)

    def update(self, frame: np.ndarray) -> tuple[float, float]:
        """Add a frame; returns (dy, dx) shift from previous frame."""
        if self._prev_frame is None:
            self._prev_frame = frame.copy()
            return 0.0, 0.0
        dy, dx = _phase_correlation_shift(self._prev_frame, frame)
        self._shifts.append((dy, dx))
        self._prev_frame = frame.copy()
        return dy, dx

    def evaluate(self, frame_index: int = 0) -> dict[str, Any] | None:
        if len(self._shifts) < 2:
            return None

        shifts = np.asarray(self._shifts, dtype=float)
        cumulative = np.sqrt(
            np.sum(shifts[:, 0]) ** 2 + np.sum(shifts[:, 1]) ** 2
        )
        if cumulative <= self.max_drift_px:
            return None

        confidence = min(1.0, cumulative / (self.max_drift_px * 2))
        return {
            "type": "MOTION",
            "confidence": round(confidence, 3),
            "summary": (
                f"Cumulative drift {cumulative:.1f}px exceeds threshold "
                f"{self.max_drift_px}px over last {len(self._shifts)} frames"
            ),
            "evidence": {
                "frame_start": max(0, frame_index - len(self._shifts)),
                "frame_end": frame_index,
                "metric_trace_ids": ["motion_dy", "motion_dx"],
            },
        }
