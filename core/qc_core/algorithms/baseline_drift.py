"""
Baseline drift detector.

Maintains a rolling window of per-frame mean intensity values and computes:
  - rolling mean
  - rolling std
  - linear slope over the window

Emits a BASELINE_DRIFT finding when:
  |slope| > baseline_drift_max_slope  OR
  rolling_std > baseline_std_max
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BaselineDriftDetector:
    window_seconds: float = 30.0
    fps: float = 30.0
    baseline_drift_max_slope: float = 0.005  # normalised units/frame
    baseline_std_max: float = 0.05  # normalised

    _intensities: deque = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        self._max_samples = int(self.window_seconds * self.fps)
        self._intensities = deque(maxlen=self._max_samples)

    def update(self, frame_mean: float) -> None:
        self._intensities.append(frame_mean)

    def evaluate(self, frame_start: int = 0) -> dict[str, Any] | None:
        """Return a Finding dict if drift detected, else None."""
        if len(self._intensities) < 2:
            return None

        arr = np.asarray(self._intensities, dtype=float)
        # Normalise by first value to get fractional changes
        baseline_val = arr[0] if arr[0] != 0 else 1.0
        norm = arr / baseline_val

        rolling_std = float(np.std(norm))
        # Linear regression slope (per-frame)
        x = np.arange(len(norm), dtype=float)
        slope = float(np.polyfit(x, norm, 1)[0])

        triggered = abs(slope) > self.baseline_drift_max_slope or rolling_std > self.baseline_std_max
        if not triggered:
            return None

        confidence = min(
            1.0,
            max(abs(slope) / self.baseline_drift_max_slope,
                rolling_std / self.baseline_std_max) * 0.5
        )
        return {
            "type": "BASELINE_DRIFT",
            "confidence": round(confidence, 3),
            "summary": (
                f"Baseline drift detected: slope={slope:.5f}/frame, "
                f"std={rolling_std:.4f} (norm)"
            ),
            "evidence": {
                "frame_start": frame_start,
                "frame_end": frame_start + len(self._intensities) - 1,
                "metric_trace_ids": ["baseline_mean", "baseline_std"],
            },
        }

    @property
    def stats(self) -> dict[str, float]:
        arr = np.asarray(self._intensities, dtype=float)
        if len(arr) == 0:
            return {"mean": 0.0, "std": 0.0, "slope": 0.0, "n": 0}
        baseline_val = arr[0] if arr[0] != 0 else 1.0
        norm = arr / baseline_val
        x = np.arange(len(norm), dtype=float)
        slope = float(np.polyfit(x, norm, 1)[0]) if len(norm) >= 2 else 0.0
        return {
            "mean": float(np.mean(norm)),
            "std": float(np.std(norm)),
            "slope": slope,
            "n": len(arr),
        }
