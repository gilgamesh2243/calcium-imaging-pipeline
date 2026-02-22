"""Performance tests (fast version for CI – 5 seconds at 30fps)."""
from __future__ import annotations

import asyncio
import pytest

from perf_tests.perf import run_perf_test


@pytest.mark.asyncio
async def test_perf_basic():
    """CI smoke test: 5s at 30fps on 64x64 frames."""
    results = await run_perf_test(
        fps=30.0,
        width=64,
        height=64,
        duration_s=5.0,
        update_interval_frames=30,
        target_fps=30.0,
        max_latency_s=5.0,  # relaxed for CI
    )
    assert results["fps_ok"], f"FPS too low: {results['actual_fps']}"
    assert results["n_status_updates"] >= 1
