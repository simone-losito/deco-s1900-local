"""Shared helpers for Deco S1900 Local Enterprise."""
from __future__ import annotations

import base64
from typing import Any


def result(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value.get("result", value) if isinstance(value, dict) else {}


def item_list(data: dict[str, Any], key: str, list_key: str) -> list[dict[str, Any]]:
    value = result(data, key).get(list_key)
    return value if isinstance(value, list) else []


def devices(data: dict[str, Any]) -> list[dict[str, Any]]:
    return item_list(data, "device_list", "device_list")


def clients(data: dict[str, Any]) -> list[dict[str, Any]]:
    return item_list(data, "clients", "client_list")


def online_clients(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [client for client in clients(data) if client.get("online") is True]


def title_name(value: Any) -> str:
    if not value:
        return ""
    text = str(value).replace("_", " ").strip()
    return " ".join(part[:1].upper() + part[1:] for part in text.split())


def decode_name(value: Any) -> str:
    if not value:
        return ""
    if not isinstance(value, str):
        return str(value)
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), validate=False).decode("utf-8", "replace").strip() or value
    except Exception:
        return value


def device_name(device: dict[str, Any]) -> str:
    return device.get("custom_nickname") or device.get("nickname") or device.get("mac") or "Deco"


def display_device_name(device: dict[str, Any]) -> str:
    return title_name(device_name(device))


def device_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {device.get("device_id"): device for device in devices(data) if device.get("device_id")}


def device_label(data: dict[str, Any], device_id: str) -> str:
    device = device_by_id(data).get(device_id, {})
    return display_device_name(device) if device else ""


def wan(data: dict[str, Any]) -> dict[str, Any]:
    return result(data, "wan").get("wan", {})


def lan(data: dict[str, Any]) -> dict[str, Any]:
    wan_result = result(data, "wan")
    if isinstance(wan_result.get("lan"), dict):
        return wan_result["lan"]
    return result(data, "lan").get("lan", result(data, "lan"))


def wireless(data: dict[str, Any]) -> dict[str, Any]:
    return result(data, "wireless")


def ip_info(block: dict[str, Any]) -> dict[str, Any]:
    return block.get("ip_info", {}) if isinstance(block, dict) else {}


def guest_status(data: dict[str, Any]) -> str:
    text = str(wireless(data)).lower()
    if "guest" not in text:
        return "Unknown"
    if "'enable': true" in text or '"enable": true' in text:
        return "On"
    if "'enable': false" in text or '"enable": false' in text:
        return "Off"
    return "Available"


def client_link(client: dict[str, Any]) -> dict[str, Any]:
    return client.get("linked_device_info") or {}


def client_device_id(client: dict[str, Any]) -> str:
    return client_link(client).get("device_id") or ""


def connection_label(raw: Any, role: str | None = None) -> str:
    conn = raw if isinstance(raw, list) else []
    if role == "master" and not conn:
        return "Master"
    if "wired" in conn:
        return "Ethernet"
    if "band5" in conn:
        return "Wi-Fi 5 GHz"
    if "band2_4" in conn:
        return "Wi-Fi 2.4 GHz"
    if conn:
        return ", ".join(str(x) for x in conn)
    return "Wireless" if role != "master" else "Master"


def signal_text(value: Any) -> str:
    try:
        value = int(value)
    except Exception:
        return "Unknown"
    if value >= 3:
        return "Excellent"
    if value == 2:
        return "Good"
    if value == 1:
        return "Weak"
    return "None"


def clients_for_node(data: dict[str, Any], device_id: str, online_only: bool = True) -> list[dict[str, Any]]:
    source = online_clients(data) if online_only else clients(data)
    return [client for client in source if client_device_id(client) == device_id]


def client_row(data: dict[str, Any], client: dict[str, Any]) -> dict[str, Any]:
    linked = client_link(client)
    signal = linked.get("signal_level") or {}
    return {
        "name": decode_name(client.get("name")),
        "ip": client.get("ip") or "",
        "mac": client.get("mac") or "",
        "type": client.get("client_type") or "",
        "online": client.get("online"),
        "deco": device_label(data, linked.get("device_id") or ""),
        "connection": connection_label(linked.get("connection_type")),
        "signal_2_4": signal.get("band2_4"),
        "signal_5": signal.get("band5"),
        "signal_quality": signal_text(max(signal.get("band2_4") or 0, signal.get("band5") or 0)),
        "priority": client.get("enable_priority"),
        "isolation": client.get("enable_isolation"),
    }


def client_summary(data: dict[str, Any], online_only: bool = True) -> list[dict[str, Any]]:
    selected = online_clients(data) if online_only else clients(data)
    return [client_row(data, client) for client in selected[:200]]


def clients_for_node_summary(data: dict[str, Any], device_id: str, online_only: bool = True) -> list[dict[str, Any]]:
    return [client_row(data, client) for client in clients_for_node(data, device_id, online_only)[:100]]


def topology_text(data: dict[str, Any]) -> str:
    nodes = devices(data)
    if not nodes:
        return "No Deco nodes found"
    master = next((n for n in nodes if n.get("role") == "master"), nodes[0])
    lines = [
        "Internet",
        "  │",
        f"  └─ {display_device_name(master)} · Master · {master.get('ip', '')} · clients:{len(clients_for_node(data, master.get('device_id') or '', True))}",
    ]
    for node in nodes:
        if node is master:
            continue
        parent = device_label(data, node.get("parent_device_id") or "")
        conn = connection_label(node.get("connection_type"), node.get("role"))
        online = len(clients_for_node(data, node.get("device_id") or "", True))
        lines.append(f"      ├─ {display_device_name(node)} · {conn} · {node.get('ip', '')} · clients:{online} · parent:{parent}")
    return "\\n".join(lines)


def firmware_consistent(data: dict[str, Any]) -> bool:
    versions = {node.get("software_ver") for node in devices(data) if node.get("software_ver")}
    return len(versions) <= 1


def wired_node_count(data: dict[str, Any]) -> int:
    return sum(1 for node in devices(data) if "wired" in (node.get("connection_type") or []))


def node_quality(node: dict[str, Any]) -> str:
    if node.get("role") == "master":
        return "Master"
    if "wired" in (node.get("connection_type") or []):
        return "Excellent"
    sig = node.get("signal_level") or {}
    return signal_text(max(sig.get("band2_4") or 0, sig.get("band5") or 0))
