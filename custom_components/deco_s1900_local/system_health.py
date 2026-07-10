"""System health information for Deco S1900 Local."""
from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, VERSION
from .helpers import devices, online_clients


@callback
def async_register(
    hass: HomeAssistant,
    register: system_health.SystemHealthRegistration,
) -> None:
    """Register system health information."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return integration health data."""
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        return {"version": VERSION, "configured_entries": 0}

    first = next(iter(entries.values()))
    coordinator = first["coordinator"]
    data = coordinator.data or {}

    return {
        "version": VERSION,
        "configured_entries": len(entries),
        "last_update_success": coordinator.last_update_success,
        "nodes": len(devices(data)),
        "clients_online": len(online_clients(data)),
    }
