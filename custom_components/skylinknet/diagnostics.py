"""Diagnostics support for SkylinkNet.

Everything here ends up in a file the user may paste into a bug report, so the
account credentials and the hub key are redacted.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_HUB_KEY, CONF_PASSWORD, DOMAIN
from .coordinator import SkylinkCoordinator

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, CONF_HUB_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SkylinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    devices = data.get("devices", {})

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "version": entry.version,
        },
        "hub": {
            "online": data.get("online"),
            "alarm_status": data.get("status"),
            "websocket_connected": getattr(coordinator.websocket, "connected", None),
            "last_update_success": coordinator.last_update_success,
        },
        "devices": [
            {
                # dev_id is a hardware id, not a secret, and it is what makes a
                # bug report actionable.
                "dev_id": dev_id,
                "name": meta.get("name"),
                "type": meta.get("type"),
                "zone": meta.get("loc"),
                "status": devices.get(dev_id, {}).get("status"),
                "battery": devices.get(dev_id, {}).get("battery"),
            }
            for dev_id, meta in coordinator.devices_meta.items()
        ],
        "device_count": len(coordinator.devices_meta),
        "reporting_count": len(devices),
    }
