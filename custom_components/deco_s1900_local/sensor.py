"""Sensors for Deco S1900 Local Enterprise."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_INCLUDE_CLIENT_DETAILS,
    CONF_MAX_CLIENTS,
    DEFAULT_INCLUDE_CLIENT_DETAILS,
    DEFAULT_MAX_CLIENTS,
    DOMAIN,
)
from .coordinator import DecoS1900Coordinator
from .helpers import (
    client_summary,
    clients,
    clients_for_node,
    clients_for_node_summary,
    connection_label,
    device_label,
    display_device_name,
    devices,
    firmware_consistent,
    guest_status,
    ip_info,
    lan,
    node_quality,
    online_clients,
    topology_text,
    wan,
    wired_node_count,
)


def mesh_status(data: dict[str, Any]) -> str:
    nodes = devices(data)
    if not nodes:
        return "Unknown"
    return "Online" if all(node.get("group_status") == "connected" for node in nodes) else "Partial"


def mesh_quality(data: dict[str, Any]) -> str:
    nodes = devices(data)
    if not nodes:
        return "Unknown"
    if all(node.get("group_status") == "connected" for node in nodes):
        if firmware_consistent(data) and wired_node_count(data) >= max(0, len(nodes) - 1):
            return "Excellent"
        return "Good"
    return "Attention"


def mesh_attributes(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "topology": topology_text(data),
        "nodes_total": len(devices(data)),
        "wired_nodes": wired_node_count(data),
        "clients_online": len(online_clients(data)),
        "clients_total": len(clients(data)),
        "firmware_consistent": firmware_consistent(data),
        "guest_wifi": guest_status(data),
        "nodes": [
            {
                "name": display_device_name(node),
                "role": node.get("role"),
                "ip": node.get("ip"),
                "mac": node.get("mac"),
                "firmware": node.get("software_ver"),
                "hardware": node.get("hardware_ver"),
                "status": node.get("group_status"),
                "internet": node.get("inet_status"),
                "connection": connection_label(node.get("connection_type"), node.get("role")),
                "quality": node_quality(node),
                "signal_2_4": (node.get("signal_level") or {}).get("band2_4"),
                "signal_5": (node.get("signal_level") or {}).get("band5"),
                "parent": "Internet" if node.get("role") == "master" else device_label(data, node.get("parent_device_id") or ""),
                "clients_online": len(clients_for_node(data, node.get("device_id") or "", True)),
            }
            for node in devices(data)
        ],
    }


@dataclass(frozen=True, kw_only=True)
class DecoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS = [
    DecoSensorDescription(key="mesh_status", name="Deco Mesh Status", icon="mdi:access-point-network", value_fn=mesh_status, attr_fn=mesh_attributes),
    DecoSensorDescription(key="mesh_quality", name="Deco Mesh Quality", icon="mdi:signal-cellular-3", value_fn=mesh_quality, attr_fn=mesh_attributes),
    DecoSensorDescription(key="nodes", name="Deco Nodes", icon="mdi:router-network", value_fn=lambda d: len(devices(d)), attr_fn=mesh_attributes),
    DecoSensorDescription(key="clients_online", name="Deco Clients Online", icon="mdi:account-network", value_fn=lambda d: len(online_clients(d)), attr_fn=lambda d: {"clients": client_summary(d, True)}),
    DecoSensorDescription(key="clients_total", name="Deco Clients Total", icon="mdi:devices", value_fn=lambda d: len(clients(d)), attr_fn=lambda d: {"clients": client_summary(d, False)}),
    DecoSensorDescription(key="guest_wifi", name="Deco Guest WiFi", icon="mdi:wifi-lock", value_fn=guest_status, attr_fn=lambda d: {"wireless_preview": str(d.get("wireless"))[:2500]}),
    DecoSensorDescription(key="wan_ip", name="Deco WAN IP", icon="mdi:wan", value_fn=lambda d: ip_info(wan(d)).get("ip", ""), attr_fn=lambda d: {"gateway": ip_info(wan(d)).get("gateway", ""), "mask": ip_info(wan(d)).get("mask", ""), "dns1": ip_info(wan(d)).get("dns1", ""), "dns2": ip_info(wan(d)).get("dns2", ""), "dial_type": wan(d).get("dial_type", ""), "mtu": wan(d).get("mtu_size", "")}),
    DecoSensorDescription(key="lan_ip", name="Deco LAN IP", icon="mdi:lan", value_fn=lambda d: ip_info(lan(d)).get("ip", ""), attr_fn=lambda d: {"mask": ip_info(lan(d)).get("mask", "")}),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: DecoS1900Coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = [DecoSensor(coordinator, entry, desc) for desc in SENSORS]

    for node in devices(coordinator.data or {}):
        node_id = node.get("device_id") or node.get("mac") or ""
        for metric in ("status", "connection", "quality", "client_count", "parent", "ip"):
            entities.append(DecoNodeSensor(coordinator, entry, node_id, metric))

    async_add_entities(entities)


class DecoSensor(CoordinatorEntity[DecoS1900Coordinator], SensorEntity):
    entity_description: DecoSensorDescription

    def __init__(self, coordinator: DecoS1900Coordinator, entry: ConfigEntry, description: DecoSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Deco S1900 Mesh",
            "manufacturer": "TP-Link",
            "model": "Deco S1900",
        }

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.entity_description.attr_fn:
            return {}
        attrs = self.entity_description.attr_fn(self.coordinator.data or {})
        if self.entity_description.key not in ("clients_online", "clients_total"):
            return attrs
        if not self.entry.options.get(
            CONF_INCLUDE_CLIENT_DETAILS,
            DEFAULT_INCLUDE_CLIENT_DETAILS,
        ):
            return {}
        limit = self.entry.options.get(CONF_MAX_CLIENTS, DEFAULT_MAX_CLIENTS)
        if isinstance(attrs.get("clients"), list):
            attrs["clients"] = attrs["clients"][:limit]
        return attrs


class DecoNodeSensor(CoordinatorEntity[DecoS1900Coordinator], SensorEntity):
    def __init__(self, coordinator: DecoS1900Coordinator, entry: ConfigEntry, node_id: str, metric: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.node_id = node_id
        self.metric = metric
        self._attr_unique_id = f"{entry.entry_id}_node_{node_id}_{metric}"

    def node(self) -> dict[str, Any]:
        for candidate in devices(self.coordinator.data or {}):
            if candidate.get("device_id") == self.node_id or candidate.get("mac") == self.node_id:
                return candidate
        return {}

    @property
    def name(self) -> str:
        label = {
            "status": "Status",
            "ip": "IP",
            "connection": "Connection",
            "quality": "Quality",
            "client_count": "Clients Online",
            "parent": "Parent Node",
        }.get(self.metric, self.metric)
        return f"Deco {display_device_name(self.node())} {label}"

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        node = self.node()
        if self.metric == "status":
            raw = node.get("group_status") or node.get("inet_status") or "unknown"
            return str(raw).title()
        if self.metric == "ip":
            return node.get("ip", "")
        if self.metric == "connection":
            return connection_label(node.get("connection_type"), node.get("role"))
        if self.metric == "parent":
            if node.get("role") == "master":
                return "Internet"
            return device_label(data, node.get("parent_device_id") or "") or "Unknown"
        if self.metric == "quality":
            return node_quality(node)
        if self.metric == "client_count":
            return len(clients_for_node(data, node.get("device_id") or "", True))
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        node = self.node()
        attrs = {
            "role": node.get("role"),
            "mac": node.get("mac"),
            "device_id": node.get("device_id"),
            "model": node.get("device_model"),
            "firmware": node.get("software_ver"),
            "hardware": node.get("hardware_ver"),
            "ip": node.get("ip"),
            "internet": node.get("inet_status"),
            "connection_type": node.get("connection_type"),
            "connection_label": connection_label(node.get("connection_type"), node.get("role")),
            "signal_level": node.get("signal_level"),
            "parent": "Internet" if node.get("role") == "master" else device_label(data, node.get("parent_device_id") or ""),
        }
        if self.metric == "client_count":
            all_clients = clients_for_node_summary(
                data,
                node.get("device_id") or "",
                True,
            )
            attrs["clients_total_on_this_deco"] = len(all_clients)
            if self.entry.options.get(
                CONF_INCLUDE_CLIENT_DETAILS,
                DEFAULT_INCLUDE_CLIENT_DETAILS,
            ):
                limit = self.entry.options.get(
                    CONF_MAX_CLIENTS,
                    DEFAULT_MAX_CLIENTS,
                )
                attrs["clients"] = all_clients[:limit]
        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        node = self.node()
        return {
            "identifiers": {(DOMAIN, self.node_id)},
            "name": f"Deco {display_device_name(node)}",
            "manufacturer": "TP-Link",
            "model": node.get("device_model") or "Deco S1900",
            "sw_version": node.get("software_ver"),
            "hw_version": node.get("hardware_ver"),
        }
