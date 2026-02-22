"""
WebSocket publisher – pushes QCStatus updates to connected dashboard clients.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WSPublisher:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("WebSocket client connected; total=%d", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        logger.info("WebSocket client disconnected; total=%d", len(self._clients))

    async def broadcast(self, data: dict[str, Any]) -> None:
        message = json.dumps(data)
        dead: set[WebSocket] = set()
        async with self._lock:
            clients = set(self._clients)
        for ws in clients:
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, RuntimeError):
                dead.add(ws)
        if dead:
            async with self._lock:
                self._clients -= dead

    async def handle(self, ws: WebSocket) -> None:
        """Full lifecycle handler for a WebSocket connection."""
        await self.connect(ws)
        try:
            while True:
                # Keep alive; client can send pings
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(ws)
