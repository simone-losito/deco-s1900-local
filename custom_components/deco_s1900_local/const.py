"""Constants for Deco S1900 Local."""
from __future__ import annotations

DOMAIN = "deco_s1900_local"
NAME = "Deco S1900 Local"
VERSION = "11.0.0"

DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 10

CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAX_CLIENTS = "max_clients"
CONF_INCLUDE_CLIENT_DETAILS = "include_client_details"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15
DEFAULT_MAX_CLIENTS = 100
DEFAULT_INCLUDE_CLIENT_DETAILS = True

ENDPOINTS = {
    "device_list": "/admin/device?form=device_list",
    "client_list": "/admin/client?form=client_list",
    "wan_ipv4": "/admin/network?form=wan_ipv4",
    "lan_ip": "/admin/network?form=lan_ip",
    "wlan": "/admin/wireless?form=wlan",
}
