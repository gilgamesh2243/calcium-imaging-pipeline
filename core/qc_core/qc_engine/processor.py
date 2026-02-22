"""
QCProcessor – consumes FrameBatch + MarkerEvent and produces QCStatus.

Maintains rolling windows and runs all detectors.
"""
from __future__ import annotations

import asyncio
import struct
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

import lz4.frame
import numpy as np

from qc_core.algorithms.baseline_drift import BaselineDriftDetector
from qc_core.algorithms.saturation import SaturationDetector
from qc_core.algorithms.motion import MotionDetector
from qc_core.algorithms.bleach import BleachDetector
from qc_core.algorithms.onset_latency import OnsetLatencyDetector
from qc_core.algorithms.focus_proxy import FocusProxyDetector
from qc_core.algorithms.marker_missing import MarkerMissingDetector

StatusCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


@dataclass
class SessionState:
    session_id: str
    fps: float = 30.0
    width: int = 512
    height: int = 512
    bit_depth: int = 16

    baseline_drift: BaselineDriftDetector = field(init=False)
    saturation: SaturationDetector = field(init=False)
    motion: MotionDetector = field(init=False)
    bleach: BleachDetector = field(init=False)
    onset_latency: OnsetLatencyDetector = field(init=False)
    focus_proxy: FocusProxyDetector = field(init=False)
    marker_missing: MarkerMissingDetector = field(init=False)

    frame_count: int = field(default=0, init=False)
    last_status: dict[str, Any] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.baseline_drift = BaselineDriftDetector(fps=self.fps)
        self.saturation = SaturationDetector(bit_depth=self.bit_depth)
        self.motion = MotionDetector()
        self.bleach = BleachDetector(fps=self.fps)
        self.onset_latency = OnsetLatencyDetector(fps=self.fps)
        self.focus_proxy = FocusProxyDetector()
        self.marker_missing = MarkerMissingDetector(fps=self.fps)
        self.marker_missing.set_session_start(0)


class QCProcessor:
    def __init__(
        self,
        status_callback: StatusCallback | None = None,
        update_interval_frames: int = 30,
    ) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._status_callback = status_callback
        self._update_interval = update_interval_frames

    def init_session(self, manifest: dict[str, Any]) -> SessionState:
        session_id = manifest["session_id"]
        channels = manifest.get("channels", [{}])
        bit_depth = channels[0].get("bit_depth", 16) if channels else 16
        state = SessionState(
            session_id=session_id,
            fps=manifest.get("fps", 30.0),
            width=manifest.get("width", 512),
            height=manifest.get("height", 512),
            bit_depth=bit_depth,
        )
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    async def process_frame_batch(self, batch: dict[str, Any]) -> dict[str, Any] | None:
        session_id = batch.get("session_id", "")
        state = self._sessions.get(session_id)
        if state is None:
            return None

        # Decompress payload
        payload = batch.get("payload", b"")
        pixel_format = batch.get("pixel_format", 2)  # UINT16
        width = batch.get("width", state.width)
        height = batch.get("height", state.height)
        frame_count = batch.get("frame_count", 1)

        frames = _decode_payload(payload, pixel_format, width, height, frame_count)
        first_frame_index = batch.get("first_frame_index", state.frame_count)

        for i, frame in enumerate(frames):
            fi = first_frame_index + i
            mean = float(np.mean(frame))

            state.baseline_drift.update(mean)
            state.bleach.update(mean)
            state.motion.update(frame)
            state.focus_proxy.update(frame)
            state.frame_count += 1

            # Periodic QC evaluation
            if state.frame_count % self._update_interval == 0:
                qc = self._evaluate(state, fi)
                if self._status_callback:
                    await self._status_callback(qc)
                state.last_status = qc
                return qc

        return None

    async def process_marker(self, event: dict[str, Any]) -> None:
        session_id = event.get("session_id", "")
        state = self._sessions.get(session_id)
        if state is None:
            return

        marker_type = event.get("type", "")
        state.marker_missing.mark_received(str(marker_type))

        if str(marker_type) in ("DRUG_ON", "3"):
            state.onset_latency.drug_on(state.frame_count)

    def _evaluate(self, state: SessionState, frame_index: int) -> dict[str, Any]:
        findings: list[dict] = []

        f = state.baseline_drift.evaluate(frame_index)
        if f:
            findings.append(f)

        f = state.motion.evaluate(frame_index)
        if f:
            findings.append(f)

        f = state.bleach.evaluate(frame_index)
        if f:
            findings.append(f)

        f = state.focus_proxy.evaluate(frame_index)
        if f:
            findings.append(f)

        f = state.onset_latency.evaluate(frame_index)
        if f:
            findings.append(f)

        findings.extend(state.marker_missing.evaluate(frame_index))

        # Score → state
        risk = _compute_risk(findings)
        state_name = "GREEN" if risk < 0.3 else ("YELLOW" if risk < 0.7 else "RED")

        return {
            "session_id": state.session_id,
            "t_eval_mono_ns": time.monotonic_ns(),
            "state": state_name,
            "risk_score": round(risk, 3),
            "top_findings": findings[:3],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _decode_payload(
    payload: bytes,
    pixel_format: int,
    width: int,
    height: int,
    frame_count: int,
) -> list[np.ndarray]:
    """Decompress LZ4 payload and split into frames."""
    if not payload:
        return [np.zeros((height, width), dtype=np.uint16)]
    try:
        raw = lz4.frame.decompress(payload)
    except Exception:
        raw = payload  # assume uncompressed (debug mode)

    dtype = np.uint16 if pixel_format == 2 else np.uint8
    try:
        arr = np.frombuffer(raw, dtype=dtype)
        expected = frame_count * height * width
        if arr.size < expected:
            arr = np.pad(arr, (0, expected - arr.size))
        frames = arr[: expected].reshape(frame_count, height, width)
        return [frames[i] for i in range(frame_count)]
    except Exception:
        return [np.zeros((height, width), dtype=np.uint16)]


def _compute_risk(findings: list[dict]) -> float:
    if not findings:
        return 0.0
    weights = {
        "BASELINE_DRIFT": 0.6,
        "FLOW_DELAY": 0.9,
        "MOTION": 0.5,
        "BLEACH": 0.7,
        "SATURATION": 0.8,
        "FOCUS_DRIFT": 0.6,
        "MARKER_MISSING": 0.85,
    }
    scores = [
        weights.get(f["type"], 0.5) * f.get("confidence", 0.5)
        for f in findings
    ]
    # Combine: max + diminishing returns for additional findings
    scores.sort(reverse=True)
    combined = scores[0]
    for s in scores[1:]:
        combined += s * (1 - combined)
    return min(1.0, combined)
