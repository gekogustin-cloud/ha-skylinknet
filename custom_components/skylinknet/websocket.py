"""Realtime WebSocket listener for a SkylinkNet hub.

The cloud exposes the same channel the official app uses:
``wss://api-1.skyhm.net/websock/hu/<hub_id>/<key>``. Once connected it pushes
the full device list (same shape as ``api/dev/read``) whenever something
changes — and periodically — plus a plain ``PING`` keepalive that clients are
expected to ignore.

Listening on this channel means state changes reach Home Assistant in about a
second instead of waiting for the next poll, while being much lighter on the
cloud than polling.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .const import WS_BASE_URL

_LOGGER = logging.getLogger(__name__)

# The app re-checks its socket every 8s; use the same cadence as a base and back
# off a bit when the cloud keeps refusing us.
RECONNECT_DELAY = 8
MAX_RECONNECT_DELAY = 120

# The server sends PING every 30s; if nothing arrives in well over that the
# connection is stale even if the socket still looks open.
RECEIVE_TIMEOUT = 90


class SkylinkWebsocket:
    """Keeps a WebSocket open and feeds device updates back to the coordinator."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        hub_id: str,
        key: str,
        on_update: Callable[[list[dict[str, Any]]], None],
        on_connection_change: Callable[[bool], None] | None = None,
    ) -> None:
        self._session = session
        self._hub_id = hub_id
        self._key = key
        self._on_update = on_update
        self._on_connection_change = on_connection_change
        self._task: asyncio.Task | None = None
        self._closing = False
        self.connected = False

    @property
    def _url(self) -> str:
        return f"{WS_BASE_URL}/websock/hu/{self._hub_id}/{self._key}"

    def start(self) -> None:
        """Start the background listener."""
        if self._task is None or self._task.done():
            self._closing = False
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the listener and close the socket."""
        self._closing = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._set_connected(False)

    def _set_connected(self, value: bool) -> None:
        if self.connected != value:
            self.connected = value
            if self._on_connection_change:
                self._on_connection_change(value)

    async def _run(self) -> None:
        delay = RECONNECT_DELAY
        while not self._closing:
            try:
                await self._listen()
                delay = RECONNECT_DELAY
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the loop alive
                _LOGGER.debug("SkylinkNet websocket error (%s); retrying", err)
                delay = min(delay * 2, MAX_RECONNECT_DELAY)
            finally:
                self._set_connected(False)

            if self._closing:
                break
            await asyncio.sleep(delay)

    async def _listen(self) -> None:
        async with self._session.ws_connect(
            self._url, heartbeat=None, receive_timeout=RECEIVE_TIMEOUT
        ) as ws:
            _LOGGER.debug("SkylinkNet websocket connected for hub %s", self._hub_id)
            self._set_connected(True)
            async for msg in ws:
                if msg.type is not aiohttp.WSMsgType.TEXT:
                    if msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.CLOSING,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        break
                    continue

                data = msg.data.strip()
                # Keepalive from the server; the official app ignores it too.
                if data == "PING":
                    continue

                try:
                    payload = json.loads(data)
                except ValueError:
                    continue

                if not isinstance(payload, dict):
                    continue
                rows = payload.get("data")
                # Device push looks like {"hub_id":..., "data":[{dev_id,status,..}]}
                # The greeting uses a dict for "data", so only lists are updates.
                if isinstance(rows, list) and rows:
                    self._on_update(rows)
