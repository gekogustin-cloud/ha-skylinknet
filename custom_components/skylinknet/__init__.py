"""The SkylinkNet Alarm integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import SkylinkNetApi
from .const import CONF_EMAIL, CONF_HUB_ID, CONF_HUB_KEY, CONF_PASSWORD, DOMAIN
from .coordinator import SkylinkCoordinator

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SkylinkNet from a config entry."""
    session = aiohttp_client.async_create_clientsession(hass)
    api = SkylinkNetApi(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = SkylinkCoordinator(
        hass, api, entry.data[CONF_HUB_ID], entry.data[CONF_HUB_KEY]
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
