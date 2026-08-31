"""Constants for Deco S1900 Local."""
from __future__ import annotations

DOMAIN = "deco_s1900_local"
NAME = "Deco S1900 Local"
VERSION = "1.0.1"

DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 10

CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15

ENDPOINTS = {
    "device_list": "/admin/device?form=device_list",
    "client_list": "/admin/client?form=client_list",
    "wan_ipv4": "/admin/network?form=wan_ipv4",
    "lan_ip": "/admin/network?form=lan_ip",
    "wlan": "/admin/wireless?form=wlan",
}
