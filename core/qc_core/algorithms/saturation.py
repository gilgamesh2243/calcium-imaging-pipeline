"""
Saturation detector.

Computes the percentage of pixels at or above max_intensity_value.
Emits SATURATION finding when % exceeds threshold.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class SaturationDetector:
    saturation_threshold_pct: float = 0.5  # % pixels saturated → warning
    bit_depth: int = 16

    @property
    def max_value(self) -> int:
        return (2**self.bit_depth) - 1

    def evaluate(
        self,
        frame: np.ndarray,
        frame_index: int = 0,
    ) -> dict[str, Any] | None:
        total = frame.size
        saturated = int(np.sum(frame >= self.max_value))
        pct = (saturated / total) * 100.0 if total > 0 else 0.0

        if pct < self.saturation_threshold_pct:
            return None

        confidence = min(1.0, pct / 100.0 * 2.0)
        return {
            "type": "SATURATION",
            "confidence": round(confidence, 3),
            "summary": (
                f"{pct:.2f}% of pixels saturated at bit-depth {self.bit_depth}"
            ),
            "evidence": {
                "frame_start": frame_index,
                "frame_end": frame_index,
                "metric_trace_ids": ["saturation_pct"],
            },
        }
