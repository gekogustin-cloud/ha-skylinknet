"""Binary sensors for SkylinkNet devices (contacts and motion)."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HUB_ALIAS, CONF_HUB_ID, DOMAIN
from .coordinator import SkylinkCoordinator

_LOGGER = logging.getLogger(__name__)

# SkylinkNet dev_type -> Home Assistant binary_sensor device class.
DEVICE_CLASS_BY_TYPE: dict[int, BinarySensorDeviceClass] = {
    4: BinarySensorDeviceClass.DOOR,
    6: BinarySensorDeviceClass.MOTION,
    11: BinarySensorDeviceClass.WINDOW,
}

# dev_types that are remotes/keypads, not monitorable sensors.
CONTROLLER_TYPES = {7}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a binary sensor for each contact/motion device on the hub."""
    coordinator: SkylinkCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [SkylinkHubConnectivity(coordinator, entry)]
    for dev_id, meta in coordinator.devices_meta.items():
        if meta.get("type") in CONTROLLER_TYPES:
            continue
        entities.append(SkylinkBinarySensor(coordinator, entry, dev_id, meta))
    async_add_entities(entities)


class SkylinkBinarySensor(CoordinatorEntity[SkylinkCoordinator], BinarySensorEntity):
    """A single SkylinkNet contact or motion sensor."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SkylinkCoordinator,
        entry: ConfigEntry,
        dev_id: str,
        meta: dict,
    ) -> None:
        super().__init__(coordinator)
        self._dev_id = dev_id
        hub_id = entry.data[CONF_HUB_ID]
        self._loc = meta.get("loc") or ""
        self._attr_name = meta.get("name") or dev_id
        self._attr_unique_id = f"skylinknet_{hub_id}_{dev_id}"
        self._attr_device_class = DEVICE_CLASS_BY_TYPE.get(
            meta.get("type"), BinarySensorDeviceClass.OPENING
        )
        # Group every entity under the same hub device.
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, hub_id)})

    @property
    def _dev(self) -> dict | None:
        data = self.coordinator.data or {}
        return data.get("devices", {}).get(self._dev_id)

    @property
    def available(self) -> bool:
        """Available while the hub is online and reporting this device."""
        data = self.coordinator.data or {}
        return super().available and data.get("online", True) and self._dev is not None

    @property
    def is_on(self) -> bool | None:
        """True = open / motion detected; None = not reporting."""
        dev = self._dev
        if not dev or dev.get("status") is None:
            return None
        return dev.get("status") == 1

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._dev or {}
        return {
            "zone": self._loc,
            "battery_low": dev.get("battery") == 0,
        }


class SkylinkHubConnectivity(
    CoordinatorEntity[SkylinkCoordinator], BinarySensorEntity
):
    """Reports whether the hub is online (reachable through the cloud).

    Unlike the other entities this one stays available while the hub is offline,
    so it can report the offline state and drive a notification automation.
    """

    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: SkylinkCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        hub_id = entry.data[CONF_HUB_ID]
        alias = (entry.data.get(CONF_HUB_ALIAS) or "").strip() or f"SkylinkNet {hub_id}"
        self._attr_name = f"{alias} Conexión"
        self._attr_unique_id = f"skylinknet_{hub_id}_online"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, hub_id)})

    @property
    def is_on(self) -> bool:
        """True = hub online."""
        data = self.coordinator.data or {}
        return bool(data.get("online", False))
