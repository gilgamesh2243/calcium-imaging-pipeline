"""
Entry point for qc-core.

Starts:
  - gRPC ingest server (port 50051)
  - FastAPI HTTP/WS server (port 8000)
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.websockets import WebSocket

from qc_core.api.routes import router, set_store
from qc_core.ingest_gateway.grpc_server import serve as grpc_serve
from qc_core.ingest_gateway.spooler import Spooler
from qc_core.qc_engine.processor import QCProcessor
from qc_core.storage.session_store import SessionStore
from qc_core.websocket.publisher import WSPublisher

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="QC Core", version="0.1.0")
_publisher = WSPublisher()
_store = SessionStore()
_spooler = Spooler()


@app.on_event("startup")
async def startup() -> None:
    await _store.open()
    set_store(_store)


@app.on_event("shutdown")
async def shutdown() -> None:
    await _store.close()


@app.websocket("/ws/qc")
async def ws_qc(websocket: WebSocket) -> None:
    await _publisher.handle(websocket)


app.include_router(router, prefix="/api/v1")


async def _main() -> None:
    processor = QCProcessor(
        status_callback=_publisher.broadcast,
        update_interval_frames=int(os.environ.get("QC_UPDATE_INTERVAL_FRAMES", "30")),
    )

    grpc_port = int(os.environ.get("QC_GRPC_PORT", "50051"))
    http_port = int(os.environ.get("QC_HTTP_PORT", "8000"))

    grpc_server = await grpc_serve(
        processor=processor,
        spooler=_spooler,
        store=_store,
        ws_publisher=_publisher,
        port=grpc_port,
    )

    config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(
        grpc_server.wait_for_termination(),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(_main())
