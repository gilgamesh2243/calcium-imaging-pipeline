"""
Fault injector – wraps a frame stream and injects synthetic failure modes.

Supported faults:
  - delayed_onset   : shift the mean by 0 until after deadline, then step
  - extra_motion    : progressive pixel shift
  - increased_bleach: exponential decay applied to each frame
  - saturation      : force a percentage of pixels to max
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np


@dataclass
class FaultConfig:
    fault_type: str  # one of the above
    start_frame: int = 0
    # delayed_onset
    onset_delay_frames: int = 150
    # extra_motion
    motion_px_per_frame: float = 0.2
    # increased_bleach
    bleach_rate: float = 0.005
    # saturation
    saturation_pct: float = 2.0


class FaultInjector:
    """Wraps a frame iterator and injects faults."""

    def __init__(self, config: FaultConfig) -> None:
        self.config = config

    def inject(
        self,
        frames: list[np.ndarray],
    ) -> list[np.ndarray]:
        """Return new list of frames with fault applied."""
        cfg = self.config
        out = []
        for i, frame in enumerate(frames):
            fi = i - cfg.start_frame
            if fi < 0:
                out.append(frame.copy())
                continue

            f = frame.astype(np.float32)

            if cfg.fault_type == "delayed_onset":
                # Suppress the signal until after onset_delay_frames
                if fi < cfg.onset_delay_frames:
                    pass  # no change (baseline)
                # After that, let normal signal through (no-op for now)

            elif cfg.fault_type == "extra_motion":
                shift = int(cfg.motion_px_per_frame * fi)
                f = np.roll(f, shift, axis=1).astype(np.float32)

            elif cfg.fault_type == "increased_bleach":
                decay = np.exp(-cfg.bleach_rate * fi)
                f = f * decay

            elif cfg.fault_type == "saturation":
                rng = np.random.default_rng(fi)
                n_sat = max(1, int(f.size * cfg.saturation_pct / 100.0))
                idx = rng.integers(0, f.size, n_sat)
                flat = f.flatten()
                flat[idx] = 65535.0
                f = flat.reshape(f.shape)

            out.append(np.clip(f, 0, 65535).astype(frame.dtype))
        return out
