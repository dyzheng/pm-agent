"""Tests for the event bus."""

import pytest
from src.server.event_bus import EventBus


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("task_updated", lambda payload: received.append(payload))
        bus.publish("task_updated", {"task_id": "FE-101"})
        assert len(received) == 1
        assert received[0]["task_id"] == "FE-101"

    def test_multiple_subscribers(self):
        bus = EventBus()
        r1, r2 = [], []
        bus.subscribe("task_updated", lambda p: r1.append(p))
        bus.subscribe("task_updated", lambda p: r2.append(p))
        bus.publish("task_updated", {"task_id": "FE-101"})
        assert len(r1) == 1
        assert len(r2) == 1

    def test_different_event_types(self):
        bus = EventBus()
        received = []
        bus.subscribe("task_updated", lambda p: received.append(p))
        bus.publish("approval_needed", {"id": "apr-001"})
        assert len(received) == 0

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        cb = lambda p: received.append(p)
        bus.subscribe("task_updated", cb)
        bus.unsubscribe("task_updated", cb)
        bus.publish("task_updated", {"task_id": "FE-101"})
        assert len(received) == 0

    def test_publish_no_subscribers(self):
        bus = EventBus()
        bus.publish("task_updated", {"task_id": "FE-101"})  # no error

    def test_subscriber_error_does_not_break_others(self):
        bus = EventBus()
        received = []

        def bad_cb(p):
            raise ValueError("boom")

        bus.subscribe("x", bad_cb)
        bus.subscribe("x", lambda p: received.append(p))
        bus.publish("x", {"v": 1})
        assert len(received) == 1
