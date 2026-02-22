"""
Focus proxy detector using Laplacian/Tenengrad energy.

Computes per-frame sharpness and detects monotonic decline indicating
focus drift.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np


def _tenengrad(frame: np.ndarray) -> float:
    """Compute Tenengrad sharpness metric (sum of squared gradient magnitudes)."""
    f = frame.astype(np.float32)
    # Simple Sobel-like gradients
    gx = np.diff(f, axis=1)
    gy = np.diff(f, axis=0)
    score = float(np.mean(gx**2) + np.mean(gy**2))
    return max(score, 1e-8)


@dataclass
class FocusProxyDetector:
    window_frames: int = 50
    monotonic_drop_threshold: float = 0.3  # fractional drop from window max

    _scores: deque = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        self._scores = deque(maxlen=self.window_frames)

    def update(self, frame: np.ndarray) -> float:
        score = _tenengrad(frame)
        self._scores.append(score)
        return score

    def evaluate(self, frame_index: int = 0) -> dict[str, Any] | None:
        if len(self._scores) < 10:
            return None

        arr = np.asarray(self._scores, dtype=float)
        window_max = float(np.max(arr))
        current = arr[-1]
        drop = (window_max - current) / (window_max + 1e-8)

        if drop < self.monotonic_drop_threshold:
            return None

        # Check if the drop is monotonic (trend is declining)
        x = np.arange(len(arr), dtype=float)
        slope = float(np.polyfit(x, arr, 1)[0])
        if slope >= 0:
            return None  # Not a declining trend

        confidence = min(1.0, drop / self.monotonic_drop_threshold)
        return {
            "type": "FOCUS_DRIFT",
            "confidence": round(confidence, 3),
            "summary": (
                f"Focus/sharpness dropped by {drop*100:.1f}% over last "
                f"{len(self._scores)} frames"
            ),
            "evidence": {
                "frame_start": max(0, frame_index - len(self._scores)),
                "frame_end": frame_index,
                "metric_trace_ids": ["focus_tenengrad"],
            },
        }
