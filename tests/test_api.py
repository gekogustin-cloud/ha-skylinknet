"""Tests for the SkylinkNet cloud client.

These use a hand-rolled session double instead of a mocking library: the client
only needs ``post`` and ``request``, and this keeps the suite working across
aiohttp releases.
"""

from __future__ import annotations

import json

import pytest

from custom_components.skylinknet.api import (
    SkylinkAuthError,
    SkylinkError,
    SkylinkNetApi,
)

EMAIL = "user@example.com"
PASSWORD = "secret"
HUB = "129039"
KEY = "12345678"

LOGIN_OK = json.dumps({"data": {"user_id": "1", "full_name": "Test"}, "errno": 0})
ACCESS_DENIED = json.dumps({"errno": 1, "message": "Access Denied"})


class FakeResponse:
    """Just enough of aiohttp's response to satisfy the client."""

    def __init__(self, body: str) -> None:
        self._body = body

    async def text(self) -> str:
        return self._body

    async def json(self, content_type=None):
        return json.loads(self._body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> bool:
        return False


class FakeSession:
    """Serves queued response bodies and records every call made."""

    def __init__(self, bodies: list[str]) -> None:
        self._bodies = list(bodies)
        self.calls: list[dict] = []

    def _next(self, entry: dict) -> FakeResponse:
        self.calls.append(entry)
        if not self._bodies:
            raise AssertionError(f"unexpected extra request: {entry}")
        return FakeResponse(self._bodies.pop(0))

    def post(self, url, data=None, **kwargs):
        return self._next({"method": "POST", "url": url, "data": data})

    def request(self, method, url, params=None, data=None, **kwargs):
        return self._next(
            {"method": method, "url": url, "params": params, "data": data}
        )


def make_api(bodies: list[str]) -> tuple[SkylinkNetApi, FakeSession]:
    session = FakeSession(bodies)
    return SkylinkNetApi(session, EMAIL, PASSWORD), session


async def test_login_success() -> None:
    """A successful login returns the profile and marks the session usable."""
    api, session = make_api([LOGIN_OK])
    data = await api.login()
    assert data["full_name"] == "Test"
    assert session.calls[0]["data"] == {"email": EMAIL, "password": PASSWORD}


async def test_login_rejects_bad_credentials() -> None:
    """errno 1 on login raises the auth error, so HA can ask to re-authenticate."""
    api, _ = make_api([ACCESS_DENIED])
    with pytest.raises(SkylinkAuthError):
        await api.login()


async def test_get_alarm_status_reads_the_hub_row() -> None:
    """The alarm state lives in the hub's own device row (F0000000)."""
    payload = json.dumps(
        {
            "errno": 0,
            "data": [
                {"dev_id": "00000001", "status": 1},
                {"dev_id": "F0000000", "status": 3},
            ],
        }
    )
    api, _ = make_api([LOGIN_OK, payload])
    assert await api.get_alarm_status(HUB, KEY) == 3


async def test_get_alarm_status_without_hub_row() -> None:
    """No hub row means we simply don't know the state."""
    api, _ = make_api([LOGIN_OK, json.dumps({"errno": 0, "data": [{"dev_id": "01"}]})])
    assert await api.get_alarm_status(HUB, KEY) is None


async def test_offline_hub_surfaces_as_error() -> None:
    """An offline hub makes the cloud answer plain text instead of JSON.

    That is exactly how offline is detected, so it must become a SkylinkError
    rather than crashing on the JSON decode.
    """
    api, _ = make_api([LOGIN_OK, "upstream request timeout"])
    with pytest.raises(SkylinkError, match="upstream request timeout"):
        await api.get_alarm_status(HUB, KEY)


async def test_set_alarm_sends_the_mode() -> None:
    api, session = make_api([LOGIN_OK, json.dumps({"errno": 0})])
    await api.set_alarm(HUB, KEY, "arm_away")
    sent = session.calls[-1]["data"]
    assert sent == {"hub_id": HUB, "key": KEY, "alarm": "arm_away"}


async def test_set_alarm_only_bypasses_when_asked() -> None:
    """bypass=1 skips open zones, so it must never be sent by accident."""
    api, session = make_api([LOGIN_OK, json.dumps({"errno": 0})])
    await api.set_alarm(HUB, KEY, "arm_home", bypass=True)
    assert session.calls[-1]["data"]["bypass"] == "1"


async def test_set_alarm_raises_on_error() -> None:
    api, _ = make_api([LOGIN_OK, json.dumps({"errno": 1, "message": "Invalid hub/Key."})])
    with pytest.raises(SkylinkError, match="Invalid hub/Key."):
        await api.set_alarm(HUB, KEY, "disarm")


async def test_get_unready_lists_open_zones() -> None:
    """These are the zones that would trip the alarm if we armed right now."""
    payload = json.dumps(
        {"errno": 0, "data": [{"dev_id": "000035A9"}, {"dev_id": "00005CCD"}]}
    )
    api, _ = make_api([LOGIN_OK, payload])
    assert await api.get_unready(HUB, KEY, "arm_away") == ["000035A9", "00005CCD"]


async def test_get_unready_is_forgiving() -> None:
    """A failure here must not block arming; worst case we arm without bypass."""
    api, _ = make_api([LOGIN_OK, json.dumps({"errno": 1, "message": "nope"})])
    assert await api.get_unready(HUB, KEY, "arm_away") == []


async def test_expired_session_relogs_in_and_retries() -> None:
    """The cookie expires after ~24h; the next call should recover on its own."""
    good = json.dumps({"errno": 0, "data": [{"dev_id": "F0000000", "status": 4}]})
    api, session = make_api([LOGIN_OK, ACCESS_DENIED, LOGIN_OK, good])
    assert await api.get_alarm_status(HUB, KEY) == 4
    # login, read (denied), login again, read again
    assert [c["method"] for c in session.calls] == ["POST", "GET", "POST", "GET"]


async def test_retry_happens_only_once() -> None:
    """If it still fails after re-logging in, give up instead of looping."""
    api, _ = make_api([LOGIN_OK, ACCESS_DENIED, LOGIN_OK, ACCESS_DENIED])
    with pytest.raises(SkylinkError):
        await api.get_alarm_status(HUB, KEY)
