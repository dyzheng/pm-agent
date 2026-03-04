"""WebSocket connection hub for broadcasting state changes to browsers."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any

from src.server.event_bus import EventBus

logger = logging.getLogger(__name__)

BROADCAST_EVENTS = [
    "task_updated",
    "approval_needed",
    "approval_resolved",
    "dispatch_started",
    "dispatch_progress",
    "dispatch_completed",
    "optimize_result",
    "state_reloaded",
]


class WebSocketHub:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus
        self._connections: list[Any] = []
        self._queue: deque[dict] = deque()
        self._loop: asyncio.AbstractEventLoop | None = None
        for event_type in BROADCAST_EVENTS:
            self._bus.subscribe(event_type, self._on_event(event_type))

    def _on_event(self, event_type: str):
        def handler(payload: dict[str, Any]) -> None:
            msg = {"type": event_type, "payload": payload}
            self._queue.append(msg)
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future, self._flush_queue()
                )
        return handler

    async def _flush_queue(self) -> None:
        while self._queue:
            msg = self._queue.popleft()
            await self.broadcast(msg)

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: Any) -> None:
        self._connections.append(websocket)
        logger.info("WebSocket connected, total: %d", len(self._connections))

    def disconnect(self, websocket: Any) -> None:
        try:
            self._connections.remove(websocket)
        except ValueError:
            pass
        logger.info("WebSocket disconnected, total: %d", len(self._connections))

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._connections:
            return
        text = json.dumps(message)
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
