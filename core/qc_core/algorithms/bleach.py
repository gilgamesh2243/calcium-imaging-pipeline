"""
Photobleach detector.

Fits a simple exponential decay y = A * exp(-k * t) to the rolling mean trace.
Triggers BLEACH finding when the estimated decay constant k exceeds threshold.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BleachDetector:
    window_seconds: float = 30.0
    fps: float = 30.0
    max_decay_constant: float = 0.001  # per-frame; flag if k > this

    _means: deque = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        self._max_samples = int(self.window_seconds * self.fps)
        self._means = deque(maxlen=self._max_samples)

    def update(self, frame_mean: float) -> None:
        self._means.append(max(frame_mean, 1e-8))

    def evaluate(self, frame_start: int = 0) -> dict[str, Any] | None:
        if len(self._means) < 10:
            return None

        arr = np.asarray(self._means, dtype=float)
        t = np.arange(len(arr), dtype=float)

        # Linearise: log(y) = log(A) - k*t
        try:
            coeffs = np.polyfit(t, np.log(arr), 1)
        except (np.linalg.LinAlgError, ValueError):
            return None

        k = -coeffs[0]  # decay constant (positive = decaying)
        if k <= self.max_decay_constant:
            return None

        confidence = min(1.0, k / (self.max_decay_constant * 5))
        return {
            "type": "BLEACH",
            "confidence": round(confidence, 3),
            "summary": (
                f"Photobleach detected: decay constant k={k:.5f}/frame "
                f"(threshold {self.max_decay_constant})"
            ),
            "evidence": {
                "frame_start": frame_start,
                "frame_end": frame_start + len(self._means) - 1,
                "metric_trace_ids": ["bleach_mean", "bleach_decay_k"],
            },
        }
