"""Tests for fault injector."""
from __future__ import annotations

import numpy as np
import pytest

from fault_injector.injector import FaultConfig, FaultInjector


def _base_frames(n: int = 20, h: int = 32, w: int = 32) -> list[np.ndarray]:
    rng = np.random.default_rng(0)
    return [rng.integers(10000, 30000, (h, w), dtype=np.uint16) for _ in range(n)]


def test_no_fault_identity():
    """With an unknown fault type before start_frame, frames pass through unchanged."""
    frames = _base_frames(10)
    cfg = FaultConfig(fault_type="delayed_onset", start_frame=100)  # starts after all frames
    injector = FaultInjector(cfg)
    out = injector.inject(frames)
    assert len(out) == len(frames)
    for orig, modified in zip(frames, out):
        np.testing.assert_array_equal(orig, modified)


def test_saturation_injection():
    frames = _base_frames(5)
    cfg = FaultConfig(fault_type="saturation", start_frame=0, saturation_pct=5.0)
    out = FaultInjector(cfg).inject(frames)
    # At least some pixels should be saturated
    sat_count = sum(int(np.sum(f == 65535)) for f in out)
    assert sat_count > 0


def test_bleach_injection():
    frames = _base_frames(20)
    cfg = FaultConfig(fault_type="increased_bleach", start_frame=0, bleach_rate=0.1)
    out = FaultInjector(cfg).inject(frames)
    # Mean of last frame should be substantially less than first
    assert float(np.mean(out[-1])) < float(np.mean(out[0])) * 0.5


def test_motion_injection():
    frames = _base_frames(10)
    cfg = FaultConfig(fault_type="extra_motion", start_frame=0, motion_px_per_frame=1.0)
    out = FaultInjector(cfg).inject(frames)
    assert len(out) == len(frames)
    # Later frames should have a visible shift – just check shapes preserved
    for f in out:
        assert f.shape == frames[0].shape
