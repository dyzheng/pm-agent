"""Tests for the WebSocket hub."""

import asyncio
import json

import pytest
from src.server.event_bus import EventBus
from src.server.websocket_hub import WebSocketHub


class FakeWebSocket:
    """Simulates a FastAPI WebSocket for testing."""

    def __init__(self):
        self.sent: list[str] = []
        self.closed = False

    async def send_text(self, data: str) -> None:
        if self.closed:
            raise RuntimeError("WebSocket closed")
        self.sent.append(data)

    async def accept(self) -> None:
        pass


@pytest.fixture
def hub():
    bus = EventBus()
    return WebSocketHub(bus)


class TestWebSocketHub:
    @pytest.mark.asyncio
    async def test_connect_and_broadcast(self, hub):
        ws = FakeWebSocket()
        await hub.connect(ws)
        assert hub.connection_count == 1
        await hub.broadcast({"type": "task_updated", "payload": {"task_id": "T-1"}})
        assert len(ws.sent) == 1
        msg = json.loads(ws.sent[0])
        assert msg["type"] == "task_updated"

    @pytest.mark.asyncio
    async def test_disconnect(self, hub):
        ws = FakeWebSocket()
        await hub.connect(ws)
        hub.disconnect(ws)
        assert hub.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple(self, hub):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await hub.connect(ws1)
        await hub.connect(ws2)
        await hub.broadcast({"type": "test", "payload": {}})
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, hub):
        ws = FakeWebSocket()
        ws.closed = True
        await hub.connect(ws)
        await hub.broadcast({"type": "test", "payload": {}})
        assert hub.connection_count == 0

    def test_event_bus_bridge(self, hub):
        """Publishing on event bus triggers broadcast queueing."""
        bus = hub._bus
        bus.publish("task_updated", {"task_id": "T-1"})
        assert len(hub._queue) == 1
