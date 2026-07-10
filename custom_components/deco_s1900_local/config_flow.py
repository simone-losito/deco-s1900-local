"""Config flow for Deco S1900 Local."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DecoAuthError, DecoConnectionError, DecoS1900Api
from .const import (
    CONF_INCLUDE_CLIENT_DETAILS,
    CONF_MAX_CLIENTS,
    CONF_SCAN_INTERVAL,
    DEFAULT_INCLUDE_CLIENT_DETAILS,
    DEFAULT_MAX_CLIENTS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


async def _validate_input(hass, host: str, password: str) -> dict[str, Any]:
    """Validate credentials and return discovered information."""
    api = DecoS1900Api(
        session=async_get_clientsession(hass),
        host=host,
        password=password,
    )
    data = await api.probe()
    result = data.get("result", data) if isinstance(data, dict) else {}
    nodes = result.get("device_list", []) if isinstance(result, dict) else []
    master = next((node for node in nodes if node.get("role") == "master"), None)
    return {
        "title": f"Deco S1900 {host}",
        "unique_id": (master or {}).get("device_id") or host,
    }


class DecoS1900ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Deco S1900 configuration."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input[CONF_PASSWORD]
            try:
                info = await _validate_input(self.hass, host, password)
            except DecoAuthError:
                errors["base"] = "invalid_auth"
            except DecoConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_HOST: host, CONF_PASSWORD: password},
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                        CONF_MAX_CLIENTS: DEFAULT_MAX_CLIENTS,
                        CONF_INCLUDE_CLIENT_DETAILS: DEFAULT_INCLUDE_CLIENT_DETAILS,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.178.68"): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Confirm updated password."""
        errors: dict[str, str] = {}
        entry = self._reauth_entry

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            try:
                await _validate_input(self.hass, entry.data[CONF_HOST], password)
            except DecoAuthError:
                errors["base"] = "invalid_auth"
            except DecoConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_PASSWORD: password},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Allow changing host and password."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            password = user_input[CONF_PASSWORD]
            try:
                await _validate_input(self.hass, host, password)
            except DecoAuthError:
                errors["base"] = "invalid_auth"
            except DecoConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={CONF_HOST: host, CONF_PASSWORD: password},
                    title=f"Deco S1900 {host}",
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=entry.data[CONF_HOST],
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return DecoS1900OptionsFlow()


class DecoS1900OptionsFlow(config_entries.OptionsFlowWithReload):
    """Manage optional integration settings."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=3600),
                ),
                vol.Required(
                    CONF_MAX_CLIENTS,
                    default=self.config_entry.options.get(
                        CONF_MAX_CLIENTS,
                        DEFAULT_MAX_CLIENTS,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=200)),
                vol.Required(
                    CONF_INCLUDE_CLIENT_DETAILS,
                    default=self.config_entry.options.get(
                        CONF_INCLUDE_CLIENT_DETAILS,
                        DEFAULT_INCLUDE_CLIENT_DETAILS,
                    ),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
