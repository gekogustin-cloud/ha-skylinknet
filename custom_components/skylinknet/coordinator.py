"""Data update coordinator for SkylinkNet."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SkylinkAuthError, SkylinkError, SkylinkNetApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SkylinkCoordinator(DataUpdateCoordinator[dict]):
    """Polls the cloud for the current alarm state of one hub."""

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

    async def _async_update_data(self) -> dict:
        try:
            status = await self.api.get_alarm_status(self.hub_id, self.key)
        except SkylinkAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SkylinkError as err:
            raise UpdateFailed(str(err)) from err
        return {"status": status}
