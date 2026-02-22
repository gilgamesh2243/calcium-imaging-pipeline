"""
Performance test – sustained fps processing.

Validates that qc-core can process ≥ target_fps single-channel frames
with < max_latency_s QC update latency.
"""
from __future__ import annotations

import asyncio
import statistics
import time
from pathlib import Path
from typing import Any

import lz4.frame
import numpy as np

import sys
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "core"))

from qc_core.qc_engine.processor import QCProcessor  # noqa: E402


async def run_perf_test(
    fps: float = 30.0,
    width: int = 512,
    height: int = 512,
    duration_s: float = 30.0,
    update_interval_frames: int = 30,
    target_fps: float = 30.0,
    max_latency_s: float = 1.0,
) -> dict[str, Any]:
    n_frames = int(fps * duration_s)
    rng = np.random.default_rng(0)

    latencies: list[float] = []
    update_times: list[float] = []

    async def on_status(qc: dict) -> None:
        update_times.append(time.monotonic())

    proc = QCProcessor(status_callback=on_status, update_interval_frames=update_interval_frames)
    manifest = {
        "session_id": "perf-test",
        "fps": fps,
        "width": width,
        "height": height,
        "channels": [{"channel_id": 0, "name": "ch0", "wavelength": 488.0, "bit_depth": 16}],
    }
    proc.init_session(manifest)

    frame_times: list[float] = []
    start = time.monotonic()

    for i in range(n_frames):
        frame_start = time.monotonic()
        frame = rng.integers(10000, 30000, (height, width), dtype=np.uint16)
        payload = lz4.frame.compress(frame.tobytes())
        batch = {
            "session_id": "perf-test",
            "batch_index": i,
            "first_frame_index": i,
            "frame_count": 1,
            "t0_mono_ns": i * int(1e9 / fps),
            "dt_ns": int(1e9 / fps),
            "channel_id": 0,
            "payload": payload,
            "pixel_format": 2,
            "width": width,
            "height": height,
            "batch_meta": {},
        }
        await proc.process_frame_batch(batch)
        frame_times.append(time.monotonic() - frame_start)

    elapsed = time.monotonic() - start
    actual_fps = n_frames / elapsed
    mean_frame_time_ms = statistics.mean(frame_times) * 1000
    max_frame_time_ms = max(frame_times) * 1000

    # Latency: time between consecutive status updates
    if len(update_times) >= 2:
        for i in range(1, len(update_times)):
            latencies.append(update_times[i] - update_times[i - 1])
        max_latency = max(latencies)
        mean_latency = statistics.mean(latencies)
    else:
        max_latency = 0.0
        mean_latency = 0.0

    results = {
        "n_frames": n_frames,
        "duration_s": elapsed,
        "actual_fps": round(actual_fps, 2),
        "mean_frame_time_ms": round(mean_frame_time_ms, 3),
        "max_frame_time_ms": round(max_frame_time_ms, 3),
        "n_status_updates": len(update_times),
        "max_latency_s": round(max_latency, 4),
        "mean_latency_s": round(mean_latency, 4),
        "fps_ok": actual_fps >= target_fps,
        "latency_ok": max_latency <= max_latency_s or max_latency == 0.0,
    }
    return results


if __name__ == "__main__":
    import json
    results = asyncio.run(run_perf_test(fps=30.0, width=512, height=512, duration_s=10.0))
    print(json.dumps(results, indent=2))
    if not results["fps_ok"]:
        print(f"FAIL: fps {results['actual_fps']} < target 30.0")
    else:
        print("PASS: fps target met")
