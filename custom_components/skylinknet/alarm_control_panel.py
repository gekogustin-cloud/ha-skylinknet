"""Alarm control panel entity for a SkylinkNet hub."""

from __future__ import annotations

import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SkylinkError
from .const import (
    CONF_HUB_ALIAS,
    CONF_HUB_ID,
    DOMAIN,
    MODE_ARM_AWAY,
    MODE_ARM_HOME,
    MODE_DISARM,
    MODE_PANIC,
    STATUS_ARMED_AWAY,
    STATUS_ARMED_HOME,
    STATUS_DISARMED,
    STATUS_DISARMED_ALT,
    STATUS_ENTRY_DELAY,
    STATUS_EXIT_DELAY,
    STATUS_PANIC,
)
from .coordinator import SkylinkCoordinator

_LOGGER = logging.getLogger(__name__)

STATUS_TO_STATE: dict[int, AlarmControlPanelState] = {
    STATUS_DISARMED_ALT: AlarmControlPanelState.DISARMED,
    STATUS_ARMED_HOME: AlarmControlPanelState.ARMED_HOME,
    STATUS_ARMED_AWAY: AlarmControlPanelState.ARMED_AWAY,
    STATUS_DISARMED: AlarmControlPanelState.DISARMED,
    STATUS_PANIC: AlarmControlPanelState.TRIGGERED,
    STATUS_ENTRY_DELAY: AlarmControlPanelState.PENDING,
    STATUS_EXIT_DELAY: AlarmControlPanelState.ARMING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the alarm panel for a config entry."""
    coordinator: SkylinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SkylinkAlarmPanel(coordinator, entry)])


class SkylinkAlarmPanel(CoordinatorEntity[SkylinkCoordinator], AlarmControlPanelEntity):
    """Represents the alarm state of one SkylinkNet hub."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.TRIGGER
    )

    def __init__(self, coordinator: SkylinkCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        hub_id = entry.data[CONF_HUB_ID]
        alias = (entry.data.get(CONF_HUB_ALIAS) or "").strip()
        self._attr_unique_id = f"skylinknet_{hub_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub_id)},
            name=alias or f"SkylinkNet {hub_id}",
            manufacturer="SkylinkNet",
            model="Internet Hub",
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state."""
        status = self.coordinator.data.get("status") if self.coordinator.data else None
        if status is None:
            return None
        return STATUS_TO_STATE.get(status)

    async def _send(self, mode: str) -> None:
        try:
            await self.coordinator.api.set_alarm(
                self.coordinator.hub_id, self.coordinator.key, mode
            )
        except SkylinkError as err:
            raise err
        await self.coordinator.async_request_refresh()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._send(MODE_DISARM)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._send(MODE_ARM_HOME)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._send(MODE_ARM_AWAY)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        await self._send(MODE_PANIC)
