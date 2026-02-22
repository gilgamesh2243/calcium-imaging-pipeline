"""
Replay server – reads a recorded session spool directory (or synthesises frames)
and re-streams it into the qc-core ingest gateway at a configurable fps.

Usage:
    python -m replay_server.server --session-dir spool/my-session --fps 30
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

import lz4.frame
import numpy as np

logger = logging.getLogger(__name__)


class ReplayServer:
    """
    Replay a session spool directory or generate synthetic data into a gRPC ingest endpoint.

    The replay server intentionally does NOT import qc_core so it can run stand-alone
    or against a remote server.  Proto stubs are generated lazily.
    """

    def __init__(
        self,
        grpc_endpoint: str = "localhost:50051",
        fps: float = 30.0,
        width: int = 512,
        height: int = 512,
        bit_depth: int = 16,
        session_id: str | None = None,
        lab_id: str = "replay-lab",
        rig_id: str = "replay-rig",
    ) -> None:
        self.grpc_endpoint = grpc_endpoint
        self.fps = fps
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.session_id = session_id or f"replay-{int(time.time())}"
        self.lab_id = lab_id
        self.rig_id = rig_id

    def _generate_synthetic_frames(
        self,
        n_frames: int,
        fault: str | None = None,
    ) -> list[np.ndarray]:
        """Generate synthetic uint16 frames with optional fault injection."""
        frames = []
        rng = np.random.default_rng(42)
        base = 20000
        for i in range(n_frames):
            frame = rng.integers(base - 500, base + 500, (self.height, self.width), dtype=np.uint16)
            if fault == "saturation":
                # 2% of pixels saturated
                n_sat = int(self.width * self.height * 0.02)
                idx = rng.integers(0, self.width * self.height, n_sat)
                flat = frame.flatten()
                flat[idx] = 65535
                frame = flat.reshape(self.height, self.width)
            elif fault == "bleach":
                decay = np.exp(-0.005 * i)
                frame = (frame * decay).astype(np.uint16)
            elif fault == "motion":
                shift = min(i // 10, 20)
                frame = np.roll(frame, shift, axis=1)
            frames.append(frame)
        return frames

    async def replay_synthetic(
        self,
        n_frames: int = 300,
        fault: str | None = None,
    ) -> None:
        """Stream synthetic frames to the ingest gateway."""
        import grpc
        from grpc import aio as grpc_aio

        # Ensure proto stubs exist
        _ensure_stubs()
        from _qcstream_generated import qcstream_pb2, qcstream_pb2_grpc  # type: ignore

        async with grpc_aio.insecure_channel(self.grpc_endpoint) as channel:
            stub = qcstream_pb2_grpc.QcIngestServiceStub(channel)

            # Send manifest
            manifest = qcstream_pb2.SessionManifest(
                session_id=self.session_id,
                lab_id=self.lab_id,
                rig_id=self.rig_id,
                modality="2p-calcium",
                width=self.width,
                height=self.height,
                fps=self.fps,
                channels=[
                    qcstream_pb2.Channel(
                        channel_id=0,
                        name="GCaMP",
                        wavelength=488.0,
                        bit_depth=self.bit_depth,
                    )
                ],
                edge_agent_version="replay/0.1.0",
                adapter_name="SimulatedAdapter",
                adapter_version="0.1.0",
            )
            await stub.SendSessionManifest(manifest)
            logger.info("Manifest sent for session %s", self.session_id)

            frames = self._generate_synthetic_frames(n_frames, fault=fault)
            dt_ns = int(1e9 / self.fps)

            async def frame_iterator():
                t0 = time.monotonic_ns()
                for i, frame in enumerate(frames):
                    payload = lz4.frame.compress(frame.tobytes())
                    yield qcstream_pb2.FrameBatch(
                        session_id=self.session_id,
                        batch_index=i,
                        first_frame_index=i,
                        frame_count=1,
                        t0_mono_ns=t0 + i * dt_ns,
                        dt_ns=dt_ns,
                        channel_id=0,
                        payload=payload,
                        pixel_format=qcstream_pb2.UINT16,
                        width=self.width,
                        height=self.height,
                    )
                    await asyncio.sleep(1.0 / self.fps)

            response = await stub.SendFrameBatches(frame_iterator())
            logger.info("Replay complete: %s", response.message)

    async def replay_from_spool(self, session_dir: str | Path) -> None:
        """Replay from a spool directory (manifest.json + markers.jsonl)."""
        import grpc
        from grpc import aio as grpc_aio

        _ensure_stubs()
        from _qcstream_generated import qcstream_pb2, qcstream_pb2_grpc  # type: ignore

        session_dir = Path(session_dir)
        manifest_path = session_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {session_dir}")

        with manifest_path.open() as f:
            manifest_data = json.load(f)

        session_id = manifest_data.get("session_id", self.session_id)
        fps = manifest_data.get("fps", self.fps)
        width = manifest_data.get("width", self.width)
        height = manifest_data.get("height", self.height)

        async with grpc_aio.insecure_channel(self.grpc_endpoint) as channel:
            stub = qcstream_pb2_grpc.QcIngestServiceStub(channel)

            channels = [
                qcstream_pb2.Channel(**ch)
                for ch in manifest_data.get("channels", [])
            ]
            manifest = qcstream_pb2.SessionManifest(
                session_id=session_id,
                lab_id=manifest_data.get("lab_id", ""),
                rig_id=manifest_data.get("rig_id", ""),
                modality=manifest_data.get("modality", ""),
                width=width,
                height=height,
                fps=fps,
                channels=channels,
                edge_agent_version=manifest_data.get("edge_agent_version", ""),
                adapter_name=manifest_data.get("adapter_name", ""),
                adapter_version=manifest_data.get("adapter_version", ""),
            )
            await stub.SendSessionManifest(manifest)

            # Synthetic frames (no raw pixel data stored in spool by default)
            n_frames = int(fps * 10)  # replay 10 seconds
            frames = self._generate_synthetic_frames(n_frames)
            dt_ns = int(1e9 / fps)

            async def frame_iterator():
                t0 = time.monotonic_ns()
                for i, frame in enumerate(frames):
                    payload = lz4.frame.compress(frame.tobytes())
                    yield qcstream_pb2.FrameBatch(
                        session_id=session_id,
                        batch_index=i,
                        first_frame_index=i,
                        frame_count=1,
                        t0_mono_ns=t0 + i * dt_ns,
                        dt_ns=dt_ns,
                        channel_id=0,
                        payload=payload,
                        pixel_format=qcstream_pb2.UINT16,
                        width=width,
                        height=height,
                    )
                    await asyncio.sleep(1.0 / fps)

            response = await stub.SendFrameBatches(frame_iterator())
            logger.info("Spool replay complete: %s", response.message)


def _ensure_stubs() -> None:
    """Generate proto stubs into _qcstream_generated/ if needed."""
    import subprocess
    import sys
    from pathlib import Path

    out_dir = Path(__file__).parent.parent / "_qcstream_generated"
    out_dir.mkdir(exist_ok=True)
    init = out_dir / "__init__.py"
    if not init.exists():
        init.write_text("")

    pb2 = out_dir / "qcstream_pb2.py"
    if pb2.exists():
        return

    proto_root = Path(__file__).parent.parent.parent / "proto"
    proto_file = proto_root / "qcstream.proto"

    result = subprocess.run(
        [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={proto_root}",
            f"--python_out={out_dir}",
            f"--grpc_python_out={out_dir}",
            str(proto_file),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"protoc failed: {result.stderr}")

    # Make imports relative
    grpc_path = out_dir / "qcstream_pb2_grpc.py"
    if grpc_path.exists():
        content = grpc_path.read_text()
        content = content.replace("import qcstream_pb2", "from _qcstream_generated import qcstream_pb2")
        grpc_path.write_text(content)

    if str(out_dir.parent) not in sys.path:
        sys.path.insert(0, str(out_dir.parent))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="localhost:50051")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--fault", choices=["saturation", "bleach", "motion"], default=None)
    parser.add_argument("--session-dir", default=None)
    parser.add_argument("--lab-id", default="replay-lab")
    parser.add_argument("--rig-id", default="replay-rig")
    args = parser.parse_args()

    server = ReplayServer(
        grpc_endpoint=args.endpoint,
        fps=args.fps,
        lab_id=args.lab_id,
        rig_id=args.rig_id,
    )

    if args.session_dir:
        asyncio.run(server.replay_from_spool(args.session_dir))
    else:
        asyncio.run(server.replay_synthetic(n_frames=args.frames, fault=args.fault))
