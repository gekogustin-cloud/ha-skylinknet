"""Tests for how pushed device data is folded into the coordinator state."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.skylinknet.coordinator import SkylinkCoordinator

HUB = "129039"
KEY = "12345678"


@pytest.fixture
def coordinator(hass):
    """A coordinator with a stubbed API (no network in these tests)."""
    api = MagicMock()
    api.read_all = AsyncMock()
    return SkylinkCoordinator(hass, api, HUB, KEY)


def test_parse_rows_splits_hub_from_sensors() -> None:
    """The F0000000 row is the alarm state; everything else is a sensor."""
    status, devices = SkylinkCoordinator._parse_rows(
        [
            {"dev_id": "F0000000", "status": 2, "battery": 1},
            {"dev_id": "00000001", "status": 1, "battery": 0},
        ]
    )
    assert status == 2
    assert "F0000000" not in devices
    assert devices["00000001"] == {"status": 1, "battery": 0}


async def test_partial_push_keeps_the_other_sensors(coordinator) -> None:
    """Regression: a single-sensor push must not blank every other entity.

    When one zone trips, the cloud pushes only that device. Replacing the whole
    device map with it used to leave every other entity unavailable and wipe the
    panel state.
    """
    coordinator.async_set_updated_data(
        {
            "online": True,
            "status": 4,
            "devices": {
                "00000001": {"status": 0, "battery": 1},
                "00000002": {"status": 0, "battery": 1},
            },
        }
    )

    # Only sensor 1 trips.
    coordinator.async_handle_push([{"dev_id": "00000001", "status": 1, "battery": 1}])

    devices = coordinator.data["devices"]
    assert devices["00000001"]["status"] == 1, "the tripped sensor should update"
    assert "00000002" in devices, "the other sensor must not disappear"
    assert devices["00000002"]["status"] == 0
    assert coordinator.data["status"] == 4, "alarm state must survive a partial push"


async def test_full_push_updates_everything(coordinator, hub_rows) -> None:
    """A full push refreshes the alarm state and every sensor."""
    coordinator.async_handle_push(hub_rows)
    assert coordinator.data["status"] == 4
    assert set(coordinator.data["devices"]) == {"00000001", "00000002"}
    assert coordinator.data["online"] is True


async def test_push_with_hub_row_updates_alarm_state(coordinator) -> None:
    """When the hub row is present, the alarm state follows it."""
    coordinator.async_set_updated_data({"online": True, "status": 4, "devices": {}})
    coordinator.async_handle_push([{"dev_id": "F0000000", "status": 3}])
    assert coordinator.data["status"] == 3


async def test_offline_keeps_last_known_state(coordinator) -> None:
    """A failed read marks the hub offline without discarding what we knew."""
    from custom_components.skylinknet.api import SkylinkError

    coordinator.async_set_updated_data(
        {"online": True, "status": 3, "devices": {"00000001": {"status": 1}}}
    )
    coordinator.api.read_all.side_effect = SkylinkError("upstream request timeout")

    data = await coordinator._async_update_data()

    assert data["online"] is False
    assert data["status"] == 3, "keep the last known alarm state"
    assert data["devices"]["00000001"]["status"] == 1
