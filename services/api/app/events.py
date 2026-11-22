"""WebSocket hub: pushes job progress, new alerts and setting changes to dashboards."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger("api.events")


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, type_: str, payload: Any = None) -> None:
        message = json.dumps({"type": type_, "payload": payload}, ensure_ascii=False, default=str)
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001 — client went away
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def publish(self, type_: str, payload: Any = None) -> None:
        """Thread-safe publish from synchronous code (DB work runs in a threadpool)."""
        if self.loop is not None:
            asyncio.run_coroutine_threadsafe(self.broadcast(type_, payload), self.loop)


hub = Hub()
