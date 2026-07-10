"""Binary sensors for Deco S1900 Local Enterprise."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DecoS1900Coordinator
from .helpers import devices


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DecoS1900Coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([DecoMeshHealthyBinarySensor(coordinator, entry)])


class DecoMeshHealthyBinarySensor(CoordinatorEntity[DecoS1900Coordinator], BinarySensorEntity):
    def __init__(self, coordinator: DecoS1900Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "Deco Mesh Healthy"
        self._attr_unique_id = f"{entry.entry_id}_mesh_healthy"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "Deco S1900 Mesh", "manufacturer": "TP-Link", "model": "Deco S1900"}

    @property
    def is_on(self) -> bool:
        nodes = devices(self.coordinator.data or {})
        return bool(nodes) and all(node.get("group_status") == "connected" for node in nodes)

    @property
    def extra_state_attributes(self) -> dict:
        nodes = devices(self.coordinator.data or {})
        return {"nodes_total": len(nodes), "nodes_connected": sum(1 for node in nodes if node.get("group_status") == "connected")}
