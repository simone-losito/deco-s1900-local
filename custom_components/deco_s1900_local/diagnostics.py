"""Diagnostics support for Deco S1900 Local."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import clients, devices, online_clients

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    data = coordinator.data or {}

    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception)
                if coordinator.last_exception
                else None
            ),
        },
        "summary": {
            "nodes": [
                {
                    "name": node.get("custom_nickname")
                    or node.get("nickname"),
                    "role": node.get("role"),
                    "model": node.get("device_model"),
                    "hardware": node.get("hardware_ver"),
                    "firmware": node.get("software_ver"),
                    "status": node.get("group_status"),
                    "internet_status": node.get("inet_status"),
                    "connection_type": node.get("connection_type"),
                }
                for node in devices(data)
            ],
            "node_count": len(devices(data)),
            "online_client_count": len(online_clients(data)),
            "known_client_count": len(clients(data)),
            "endpoint_errors": {
                key: value.get("error")
                for key, value in data.items()
                if isinstance(value, dict) and value.get("error")
            },
        },
    }
