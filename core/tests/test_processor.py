"""
Unit tests for QCProcessor.
"""
from __future__ import annotations

import asyncio

import lz4.frame
import numpy as np
import pytest

from qc_core.qc_engine.processor import QCProcessor, _decode_payload, _compute_risk


def _make_manifest(session_id: str = "test-session") -> dict:
    return {
        "session_id": session_id,
        "fps": 10.0,
        "width": 64,
        "height": 64,
        "channels": [{"channel_id": 0, "name": "GCaMP", "wavelength": 488.0, "bit_depth": 16}],
    }


def _make_batch(session_id: str, frame_index: int, frame: np.ndarray | None = None) -> dict:
    if frame is None:
        frame = np.zeros((64, 64), dtype=np.uint16)
    payload = lz4.frame.compress(frame.tobytes())
    return {
        "session_id": session_id,
        "batch_index": frame_index,
        "first_frame_index": frame_index,
        "frame_count": 1,
        "t0_mono_ns": frame_index * 100_000_000,
        "dt_ns": 100_000_000,
        "channel_id": 0,
        "payload": payload,
        "pixel_format": 2,
        "width": 64,
        "height": 64,
        "batch_meta": {},
    }


@pytest.mark.asyncio
async def test_init_session():
    proc = QCProcessor()
    manifest = _make_manifest()
    state = proc.init_session(manifest)
    assert state.session_id == "test-session"
    assert state.fps == 10.0


@pytest.mark.asyncio
async def test_process_frames_returns_qc_at_interval():
    received = []

    async def on_status(qc):
        received.append(qc)

    proc = QCProcessor(status_callback=on_status, update_interval_frames=5)
    proc.init_session(_make_manifest())

    for i in range(10):
        await proc.process_frame_batch(_make_batch("test-session", i))

    assert len(received) >= 1
    for qc in received:
        assert qc["session_id"] == "test-session"
        assert qc["state"] in ("GREEN", "YELLOW", "RED")
        assert 0.0 <= qc["risk_score"] <= 1.0


@pytest.mark.asyncio
async def test_process_marker():
    proc = QCProcessor()
    proc.init_session(_make_manifest())
    event = {
        "session_id": "test-session",
        "t_mono_ns": 1_000_000,
        "type": "DRUG_ON",
        "value": "",
        "meta": {},
    }
    await proc.process_marker(event)  # Should not raise


def test_decode_payload_lz4():
    frame = np.ones((64, 64), dtype=np.uint16) * 500
    payload = lz4.frame.compress(frame.tobytes())
    frames = _decode_payload(payload, 2, 64, 64, 1)
    assert len(frames) == 1
    assert frames[0].shape == (64, 64)


def test_compute_risk_empty():
    assert _compute_risk([]) == 0.0


def test_compute_risk_findings():
    findings = [
        {"type": "SATURATION", "confidence": 0.9},
        {"type": "MOTION", "confidence": 0.5},
    ]
    risk = _compute_risk(findings)
    assert 0.0 < risk <= 1.0
