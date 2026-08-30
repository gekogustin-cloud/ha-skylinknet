"""The SkylinkNet Alarm integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import SkylinkNetApi
from .const import CONF_EMAIL, CONF_HUB_ID, CONF_HUB_KEY, CONF_PASSWORD, DOMAIN
from .coordinator import SkylinkCoordinator
from .websocket import SkylinkWebsocket

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SkylinkNet from a config entry."""
    session = aiohttp_client.async_create_clientsession(hass)
    api = SkylinkNetApi(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = SkylinkCoordinator(
        hass, api, entry.data[CONF_HUB_ID], entry.data[CONF_HUB_KEY]
    )
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_load_devices()

    # Realtime updates: the cloud pushes the full device list on this channel,
    # so the poll above is only a fallback.
    websocket = SkylinkWebsocket(
        session,
        entry.data[CONF_HUB_ID],
        entry.data[CONF_HUB_KEY],
        coordinator.async_handle_push,
    )
    websocket.start()
    coordinator.websocket = websocket

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: SkylinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.websocket:
        await coordinator.websocket.stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
