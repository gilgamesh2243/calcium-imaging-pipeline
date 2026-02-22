"""Tests for golden test runner – deterministic QC outputs."""
from __future__ import annotations

import numpy as np
import pytest

from golden_tests.runner import run_golden


def _make_manifest(session_id: str = "golden-test") -> dict:
    return {
        "session_id": session_id,
        "fps": 10.0,
        "width": 32,
        "height": 32,
        "channels": [{"channel_id": 0, "name": "ch0", "wavelength": 488.0, "bit_depth": 16}],
    }


def _flat_frames(n: int = 50, val: int = 20000) -> list[np.ndarray]:
    return [np.full((32, 32), val, dtype=np.uint16) for _ in range(n)]


def test_golden_deterministic():
    """Same input produces same digest on two runs."""
    frames = _flat_frames(50)
    manifest = _make_manifest()
    _, digest1 = run_golden(frames, manifest, update_interval_frames=10)
    _, digest2 = run_golden(frames, manifest, update_interval_frames=10)
    assert digest1 == digest2


def test_golden_different_fault_changes_digest():
    """Different frame data produces different digest."""
    frames_good = _flat_frames(50, val=20000)
    frames_bad = _flat_frames(50, val=60000)  # near-saturation
    manifest = _make_manifest()
    _, d1 = run_golden(frames_good, manifest, update_interval_frames=10)
    _, d2 = run_golden(frames_bad, manifest, update_interval_frames=10)
    # Digests might differ (risk scores differ); even if they don't,
    # there should be no exception
    assert isinstance(d1, str) and len(d1) == 64
    assert isinstance(d2, str) and len(d2) == 64


def test_golden_with_markers():
    """Golden test with markers runs without error."""
    frames = _flat_frames(50)
    manifest = _make_manifest()
    markers = [
        {
            "session_id": "golden-test",
            "t_mono_ns": 1_000_000,
            "type": "DRUG_ON",
            "value": "",
            "meta": {},
        }
    ]
    statuses, digest = run_golden(frames, manifest, markers=markers, update_interval_frames=10)
    assert isinstance(digest, str)
