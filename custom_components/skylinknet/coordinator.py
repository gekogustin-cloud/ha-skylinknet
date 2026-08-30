"""Data update coordinator for SkylinkNet."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SkylinkAuthError, SkylinkError, SkylinkNetApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, HUB_DEV_ID

_LOGGER = logging.getLogger(__name__)


class SkylinkCoordinator(DataUpdateCoordinator[dict]):
    """Polls the cloud for the alarm state and every sensor of one hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SkylinkNetApi,
        hub_id: str,
        key: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{hub_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.hub_id = hub_id
        self.key = key
        # dev_id -> {"name": str, "type": int, "loc": str}
        self.devices_meta: dict[str, dict] = {}

    async def async_load_devices(self) -> None:
        """Fetch the (mostly static) device metadata once, at setup."""
        try:
            devices = await self.api.get_devices(self.hub_id, self.key)
        except SkylinkError as err:
            _LOGGER.warning("Could not load SkylinkNet devices: %s", err)
            return
        self.devices_meta = {
            dev["dev_id"]: {
                "name": dev.get("dev_name"),
                "type": dev.get("dev_type"),
                "loc": dev.get("dev_loc"),
            }
            for dev in devices
            if dev.get("dev_id")
        }

    async def _async_update_data(self) -> dict:
        try:
            rows = await self.api.read_all(self.hub_id, self.key)
        except SkylinkAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SkylinkError as err:
            raise UpdateFailed(str(err)) from err

        hub_status: int | None = None
        devices: dict[str, dict] = {}
        for row in rows:
            dev_id = row.get("dev_id")
            if not dev_id:
                continue
            if dev_id == HUB_DEV_ID:
                hub_status = row.get("status")
            else:
                devices[dev_id] = {
                    "status": row.get("status"),
                    "battery": row.get("battery"),
                }
        return {"status": hub_status, "devices": devices}
