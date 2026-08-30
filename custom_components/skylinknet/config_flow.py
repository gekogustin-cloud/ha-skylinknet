"""Config flow for the SkylinkNet integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import aiohttp_client

from .api import SkylinkAuthError, SkylinkError, SkylinkNetApi
from .const import (
    CONF_EMAIL,
    CONF_HUB_ALIAS,
    CONF_HUB_ID,
    CONF_HUB_KEY,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SkylinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the SkylinkNet configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._hubs: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: account email + password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = aiohttp_client.async_create_clientsession(self.hass)
            api = SkylinkNetApi(
                session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            try:
                await api.login()
                self._hubs = await api.get_hubs()
            except SkylinkAuthError:
                errors["base"] = "invalid_auth"
            except SkylinkError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during SkylinkNet login")
                errors["base"] = "unknown"
            else:
                if not self._hubs:
                    errors["base"] = "no_hubs"
                else:
                    self._email = user_input[CONF_EMAIL]
                    self._password = user_input[CONF_PASSWORD]
                    return await self.async_step_hub()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: pick the hub and enter its key (Hub Password)."""
        errors: dict[str, str] = {}
        hub_options = {
            hub["hub_id"]: f"{(hub.get('hub_alias') or '').strip()} ({hub['hub_id']})"
            for hub in self._hubs
        }

        if user_input is not None:
            hub_id = user_input[CONF_HUB_ID]
            key = user_input[CONF_HUB_KEY]

            await self.async_set_unique_id(f"skylinknet_{hub_id}")
            self._abort_if_unique_id_configured()

            session = aiohttp_client.async_create_clientsession(self.hass)
            api = SkylinkNetApi(session, self._email, self._password)
            try:
                await api.login()
                status = await api.get_alarm_status(hub_id, key)
            except SkylinkError:
                errors["base"] = "invalid_key"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating SkylinkNet hub key")
                errors["base"] = "unknown"
            else:
                if status is None:
                    errors["base"] = "invalid_key"
                else:
                    alias = next(
                        (
                            (hub.get("hub_alias") or "").strip()
                            for hub in self._hubs
                            if hub["hub_id"] == hub_id
                        ),
                        "",
                    )
                    return self.async_create_entry(
                        title=alias or f"SkylinkNet {hub_id}",
                        data={
                            CONF_EMAIL: self._email,
                            CONF_PASSWORD: self._password,
                            CONF_HUB_ID: hub_id,
                            CONF_HUB_KEY: key,
                            CONF_HUB_ALIAS: alias,
                        },
                    )

        return self.async_show_form(
            step_id="hub",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HUB_ID): vol.In(hub_options),
                    vol.Required(CONF_HUB_KEY): str,
                }
            ),
            errors=errors,
        )
