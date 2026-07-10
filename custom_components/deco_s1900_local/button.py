"""Buttons for Deco S1900 Local Enterprise."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DecoS1900Coordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DecoS1900Coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([DecoRefreshButton(coordinator, entry)])


class DecoRefreshButton(CoordinatorEntity[DecoS1900Coordinator], ButtonEntity):
    def __init__(self, coordinator: DecoS1900Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "Deco Refresh"
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_class = ButtonDeviceClass.UPDATE
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "Deco S1900 Mesh", "manufacturer": "TP-Link", "model": "Deco S1900"}

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
