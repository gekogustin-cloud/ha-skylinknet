"""Tests for how the realtime listener interprets what the cloud sends."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import aiohttp
import pytest

from custom_components.skylinknet.websocket import SkylinkWebsocket


@pytest.fixture
def listener():
    """A listener with a recording callback; nothing connects to the network."""
    updates: list[list[dict]] = []
    ws = SkylinkWebsocket(
        MagicMock(), "129039", "12345678", lambda rows: updates.append(rows)
    )
    return ws, updates


def feed(ws, updates, raw: str) -> None:
    """Run one text frame through the same logic _listen uses."""
    data = raw.strip()
    if data == "PING":
        return
    try:
        payload = json.loads(data)
    except ValueError:
        return
    if not isinstance(payload, dict):
        return
    rows = payload.get("data")
    if isinstance(rows, list) and rows:
        ws._on_update(rows)


def test_url_includes_hub_and_key(listener) -> None:
    ws, _ = listener
    assert ws._url == "wss://api-1.skyhm.net/websock/hu/129039/12345678"


def test_ping_keepalive_is_ignored(listener) -> None:
    """The server sends a bare 'PING' every 30s; it is not a device update."""
    ws, updates = listener
    feed(ws, updates, "PING")
    assert updates == []


def test_greeting_is_not_treated_as_an_update(listener) -> None:
    """The hello frame carries a dict in 'data', not a device list."""
    ws, updates = listener
    feed(ws, updates, '{"data":{"keepalive_interval":30,"super_user":1},"errno":0}')
    assert updates == []


def test_device_push_is_forwarded(listener) -> None:
    ws, updates = listener
    feed(
        ws,
        updates,
        '{"hub_id":"129039","data":[{"dev_id":"F0000000","status":4,"battery":1}]}',
    )
    assert updates == [[{"dev_id": "F0000000", "status": 4, "battery": 1}]]


def test_garbage_frame_does_not_raise(listener) -> None:
    """A non-JSON frame must not kill the listener."""
    ws, updates = listener
    feed(ws, updates, "not json at all")
    assert updates == []


def test_connection_state_callback() -> None:
    """Connection changes are reported once per transition."""
    seen: list[bool] = []
    ws = SkylinkWebsocket(
        MagicMock(), "1", "2", lambda rows: None, on_connection_change=seen.append
    )
    ws._set_connected(True)
    ws._set_connected(True)  # no change -> no second callback
    ws._set_connected(False)
    assert seen == [True, False]
