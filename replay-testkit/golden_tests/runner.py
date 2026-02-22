"""
Golden test runner.

Given an input frame sequence + config, runs the QC algorithms deterministically
and produces a hash of the QCStatus timeline.  Comparing this hash across runs
verifies reproducibility (NIH-grade audit).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

# The golden tests run the algorithms in-process (no gRPC needed)
import sys

# Allow importing qc_core from sibling directory
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "core"))

from qc_core.qc_engine.processor import QCProcessor, _compute_risk  # noqa: E402
import lz4.frame


def run_golden(
    frames: list[np.ndarray],
    manifest: dict[str, Any],
    markers: list[dict[str, Any]] | None = None,
    update_interval_frames: int = 10,
) -> tuple[list[dict[str, Any]], str]:
    """
    Run QC on frames + manifest and return (statuses, sha256_hash).

    The hash is computed over the ordered list of QCStatus dicts (JSON, sorted keys).
    This is deterministic given the same input.
    """
    import asyncio

    statuses: list[dict[str, Any]] = []

    async def _run():
        nonlocal statuses

        async def cb(qc: dict) -> None:
            statuses.append(qc)

        proc = QCProcessor(status_callback=cb, update_interval_frames=update_interval_frames)
        proc.init_session(manifest)

        if markers:
            for m in markers:
                await proc.process_marker(m)

        width = manifest.get("width", 64)
        height = manifest.get("height", 64)

        for i, frame in enumerate(frames):
            payload = lz4.frame.compress(frame.tobytes())
            batch = {
                "session_id": manifest["session_id"],
                "batch_index": i,
                "first_frame_index": i,
                "frame_count": 1,
                "t0_mono_ns": i * 100_000_000,
                "dt_ns": 100_000_000,
                "channel_id": 0,
                "payload": payload,
                "pixel_format": 2,
                "width": width,
                "height": height,
                "batch_meta": {},
            }
            await proc.process_frame_batch(batch)

    asyncio.run(_run())

    # Remove non-deterministic fields (timestamps)
    clean = []
    for s in statuses:
        c = {k: v for k, v in s.items() if k != "t_eval_mono_ns"}
        clean.append(c)

    digest = hashlib.sha256(
        json.dumps(clean, sort_keys=True, default=str).encode()
    ).hexdigest()
    return statuses, digest


def save_golden(output_path: Path, digest: str, statuses: list[dict]) -> None:
    output_path.write_text(json.dumps({"digest": digest, "statuses": statuses}, indent=2))


def verify_golden(golden_path: Path, frames: list[np.ndarray], manifest: dict, **kwargs) -> bool:
    golden = json.loads(golden_path.read_text())
    _, digest = run_golden(frames, manifest, **kwargs)
    return digest == golden["digest"]
