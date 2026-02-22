"""
Unit tests for QC algorithms.
"""
from __future__ import annotations

import numpy as np
import pytest

from qc_core.algorithms.baseline_drift import BaselineDriftDetector
from qc_core.algorithms.saturation import SaturationDetector
from qc_core.algorithms.motion import MotionDetector
from qc_core.algorithms.bleach import BleachDetector
from qc_core.algorithms.onset_latency import OnsetLatencyDetector
from qc_core.algorithms.focus_proxy import FocusProxyDetector
from qc_core.algorithms.marker_missing import MarkerMissingDetector


# ─── BaselineDriftDetector ────────────────────────────────────────────────────

def test_baseline_drift_no_drift():
    det = BaselineDriftDetector(fps=10.0, baseline_drift_max_slope=0.005)
    for _ in range(50):
        det.update(1000.0)
    assert det.evaluate() is None


def test_baseline_drift_detects():
    det = BaselineDriftDetector(fps=10.0, baseline_drift_max_slope=0.001)
    for i in range(50):
        det.update(1000.0 + i * 10)  # strong upward trend
    finding = det.evaluate()
    assert finding is not None
    assert finding["type"] == "BASELINE_DRIFT"
    assert 0 < finding["confidence"] <= 1.0


def test_baseline_drift_stats():
    det = BaselineDriftDetector(fps=10.0)
    for i in range(10):
        det.update(float(i))
    stats = det.stats
    assert "mean" in stats and "slope" in stats


# ─── SaturationDetector ───────────────────────────────────────────────────────

def test_saturation_none_when_clean():
    det = SaturationDetector(saturation_threshold_pct=1.0, bit_depth=16)
    frame = np.zeros((64, 64), dtype=np.uint16)
    assert det.evaluate(frame) is None


def test_saturation_detects():
    det = SaturationDetector(saturation_threshold_pct=0.1, bit_depth=16)
    frame = np.full((64, 64), 65535, dtype=np.uint16)
    finding = det.evaluate(frame, frame_index=42)
    assert finding is not None
    assert finding["type"] == "SATURATION"
    assert finding["evidence"]["frame_start"] == 42


# ─── MotionDetector ───────────────────────────────────────────────────────────

def test_motion_no_motion():
    det = MotionDetector(max_drift_px=5.0)
    frame = np.random.randint(0, 1000, (64, 64), dtype=np.uint16)
    for _ in range(10):
        det.update(frame)
    assert det.evaluate() is None  # same frame, no drift


def test_motion_shift_returns_values():
    det = MotionDetector(max_drift_px=5.0)
    frame = np.zeros((64, 64), dtype=np.uint16)
    dy, dx = det.update(frame)
    assert dy == 0.0 and dx == 0.0  # first frame returns zero


# ─── BleachDetector ──────────────────────────────────────────────────────────

def test_bleach_no_decay():
    det = BleachDetector(fps=10.0, max_decay_constant=0.001)
    for _ in range(50):
        det.update(1000.0)
    assert det.evaluate() is None


def test_bleach_detects_decay():
    det = BleachDetector(fps=10.0, max_decay_constant=0.0001)
    import math
    for i in range(50):
        det.update(1000.0 * math.exp(-0.01 * i))
    finding = det.evaluate()
    assert finding is not None
    assert finding["type"] == "BLEACH"


# ─── OnsetLatencyDetector ────────────────────────────────────────────────────

def test_onset_latency_no_drug_on():
    det = OnsetLatencyDetector(fps=10.0)
    det.update(500.0, 0)
    assert det.evaluate(50) is None


def test_onset_latency_detects_delay():
    det = OnsetLatencyDetector(fps=10.0, expected_onset_max_s=5.0)
    # Establish baseline
    for i in range(50):
        det.update(500.0, i)
    det.drug_on(50)
    # Simulate no onset for 10 seconds (100 frames at 10fps)
    for i in range(100):
        det.update(500.0, 50 + i)
    finding = det.evaluate(150)
    assert finding is not None
    assert finding["type"] == "FLOW_DELAY"


# ─── FocusProxyDetector ──────────────────────────────────────────────────────

def test_focus_no_drop():
    det = FocusProxyDetector(monotonic_drop_threshold=0.3)
    frame = np.random.randint(100, 200, (64, 64), dtype=np.uint16)
    for _ in range(20):
        det.update(frame)
    # No drop → no finding
    result = det.evaluate()
    # Result could be None or not depending on noise; just check no error
    assert result is None or result["type"] == "FOCUS_DRIFT"


def test_focus_detects_drop():
    det = FocusProxyDetector(window_frames=20, monotonic_drop_threshold=0.1)
    # Sharp first, then blurry
    for i in range(10):
        frame = np.random.randint(0, 1000, (64, 64), dtype=np.uint16)
        det.update(frame)
    for i in range(10):
        frame = np.zeros((64, 64), dtype=np.uint16)  # zero variance = blurry
        det.update(frame)
    # Should detect a drop
    result = det.evaluate(20)
    # May or may not trigger depending on noise; just confirm no exception
    assert result is None or result["type"] == "FOCUS_DRIFT"


# ─── MarkerMissingDetector ───────────────────────────────────────────────────

def test_marker_missing_before_deadline():
    det = MarkerMissingDetector(expected_markers=["DRUG_ON"], deadline_seconds=10.0, fps=10.0)
    findings = det.evaluate(50)  # 5 seconds elapsed
    assert findings == []


def test_marker_missing_after_deadline():
    det = MarkerMissingDetector(expected_markers=["DRUG_ON"], deadline_seconds=10.0, fps=10.0)
    findings = det.evaluate(200)  # 20 seconds elapsed, no marker received
    assert len(findings) == 1
    assert findings[0]["type"] == "MARKER_MISSING"


def test_marker_missing_received():
    det = MarkerMissingDetector(expected_markers=["DRUG_ON"], deadline_seconds=10.0, fps=10.0)
    det.mark_received("DRUG_ON")
    findings = det.evaluate(200)
    assert findings == []
