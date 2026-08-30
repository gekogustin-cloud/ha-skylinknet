"""Async client for the SkylinkNet cloud API (api-1.skyhm.net).

The API has no separate token: the user session is a cookie obtained from
``guest/login`` (account email + password). Per-hub operations additionally
require the hub ``key`` (the "Hub Password" set when the hub was first
configured). Both the reads and the commands need the session cookie.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import BASE_URL, HUB_DEV_ID

_LOGGER = logging.getLogger(__name__)

# Cap every request so a hub-offline "upstream request timeout" from the cloud
# doesn't hang the poll for minutes.
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


class SkylinkError(Exception):
    """A generic SkylinkNet API error."""


class SkylinkAuthError(SkylinkError):
    """Login failed (bad account email/password) or the session is invalid."""


class SkylinkNetApi:
    """Minimal async wrapper over the SkylinkNet cloud endpoints we need."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._logged_in = False
        self._lock = asyncio.Lock()

    async def login(self) -> dict[str, Any]:
        """Authenticate the account and store the session cookie."""
        payload = {"email": self._email, "password": self._password}
        try:
            async with self._session.post(
                f"{BASE_URL}/guest/login", data=payload
            ) as resp:
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise SkylinkError(f"Connection error during login: {err}") from err

        if not isinstance(data, dict) or data.get("errno") != 0:
            message = ""
            if isinstance(data, dict):
                message = str(data.get("message", ""))
            raise SkylinkAuthError(message or "Login failed")

        self._logged_in = True
        return data.get("data", {})

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.login()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        _retry: bool = True,
    ) -> Any:
        """Perform a request, transparently re-logging in if the session died."""
        async with self._lock:
            await self._ensure_login()

        url = f"{BASE_URL}/{path}"
        try:
            async with self._session.request(
                method, url, params=params, data=data, timeout=REQUEST_TIMEOUT
            ) as resp:
                text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SkylinkError(f"Connection error on {path}: {err}") from err

        try:
            body = json.loads(text)
        except ValueError:
            # Non-JSON body: the cloud returns "upstream request timeout" (plain
            # text) when it cannot reach the hub, i.e. the hub is offline.
            raise SkylinkError(text.strip()[:120] or "Empty response")

        # Expired/invalid session -> the API answers "Access Denied". Re-login once.
        if (
            _retry
            and isinstance(body, dict)
            and body.get("errno") == 1
            and "Access Denied" in str(body.get("message", ""))
        ):
            self._logged_in = False
            async with self._lock:
                await self.login()
            return await self._request(
                method, path, params=params, data=data, _retry=False
            )

        return body

    async def get_hubs(self) -> list[dict[str, Any]]:
        """Return the hubs registered on the account."""
        body = await self._request("GET", "api/user/get_hub")
        if not isinstance(body, dict) or body.get("errno") != 0:
            raise SkylinkError("Could not list hubs")
        return body.get("data", []) or []

    async def get_alarm_status(self, hub_id: str, key: str) -> int | None:
        """Return the current alarm status integer for the hub, or None."""
        body = await self._request(
            "GET", "api/dev/read", params={"hub_id": hub_id, "key": key}
        )
        if not isinstance(body, dict) or body.get("errno") != 0:
            message = ""
            if isinstance(body, dict):
                message = str(body.get("message", ""))
            raise SkylinkError(message or "Could not read alarm status")
        for dev in body.get("data", []) or []:
            if dev.get("dev_id") == HUB_DEV_ID:
                return dev.get("status")
        return None

    async def get_devices(self, hub_id: str, key: str) -> list[dict[str, Any]]:
        """Return the sensors/devices paired to the hub (names, types, zones)."""
        body = await self._request(
            "GET", "api/dev/get_dev", params={"hub_id": hub_id, "key": key}
        )
        if not isinstance(body, dict) or body.get("errno") != 0:
            raise SkylinkError("Could not read devices")
        return body.get("data", []) or []

    async def read_all(self, hub_id: str, key: str) -> list[dict[str, Any]]:
        """Return live status/battery for every device (incl. the hub F0000000)."""
        body = await self._request(
            "GET", "api/dev/read", params={"hub_id": hub_id, "key": key}
        )
        if not isinstance(body, dict) or body.get("errno") != 0:
            message = ""
            if isinstance(body, dict):
                message = str(body.get("message", ""))
            raise SkylinkError(message or "Could not read device states")
        return body.get("data", []) or []

    async def get_unready(self, hub_id: str, key: str, mode: str) -> list[str]:
        """Return the dev_ids of sensors that are not ready (open) for a mode.

        Arming while a zone is open (with no exit delay) makes the hub trigger
        immediately, so callers check this first and arm with ``bypass`` if the
        list is non-empty (this mirrors the official app).
        """
        body = await self._request(
            "GET",
            "api/alarm/get_unready",
            params={"hub_id": hub_id, "key": key, "alarm": mode},
        )
        if not isinstance(body, dict) or body.get("errno") != 0:
            return []
        return [
            dev.get("dev_id")
            for dev in body.get("data", []) or []
            if dev.get("dev_id")
        ]

    async def set_alarm(
        self, hub_id: str, key: str, mode: str, bypass: bool = False
    ) -> None:
        """Set the hub mode: arm_home, arm_away, disarm or panic.

        When ``bypass`` is True, open ("not ready") zones are bypassed so the
        system arms instead of triggering immediately.
        """
        data = {"hub_id": hub_id, "key": key, "alarm": mode}
        if bypass:
            data["bypass"] = "1"
        body = await self._request("POST", "api/alarm/set_alarm", data=data)
        if not isinstance(body, dict) or body.get("errno") != 0:
            message = ""
            if isinstance(body, dict):
                message = str(body.get("message", ""))
            raise SkylinkError(message or f"set_alarm '{mode}' failed")
