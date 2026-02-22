"""
Utility to generate Python gRPC stubs from proto/qcstream.proto at import time
(only if the generated files are missing).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROTO_ROOT = Path(__file__).parent.parent.parent / "proto"
OUT_DIR = Path(__file__).parent / "generated"


def ensure_generated() -> None:
    """Generate *_pb2.py / *_pb2_grpc.py if not present."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    init = OUT_DIR / "__init__.py"
    if not init.exists():
        init.write_text("")

    pb2 = OUT_DIR / "qcstream_pb2.py"
    if pb2.exists():
        return

    proto_file = PROTO_ROOT / "qcstream.proto"
    if not proto_file.exists():
        raise FileNotFoundError(f"Proto file not found: {proto_file}")

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={PROTO_ROOT}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        str(proto_file),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"protoc failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
