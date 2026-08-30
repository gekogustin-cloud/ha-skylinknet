"""Constants for the SkylinkNet integration."""

from __future__ import annotations

DOMAIN = "skylinknet"

# Config entry keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_HUB_ID = "hub_id"
CONF_HUB_KEY = "key"
CONF_HUB_ALIAS = "hub_alias"

# SkylinkNet cloud API
BASE_URL = "https://api-1.skyhm.net"
WS_BASE_URL = "wss://api-1.skyhm.net"

# The special device id that represents the hub's own alarm state.
HUB_DEV_ID = "F0000000"

# Event fired on the HA bus every time the panel arms (for notifications).
EVENT_ARMED = "skylinknet_armed"

# Fallback poll interval. State normally arrives over the WebSocket within a
# second, so this only exists to recover if that channel goes quiet.
DEFAULT_SCAN_INTERVAL = 600

# Hub alarm "status" integer -> meaning (from the hub firmware / app).
STATUS_DISARMED_ALT = 0
STATUS_ARMED_HOME = 2
STATUS_ARMED_AWAY = 3
STATUS_DISARMED = 4
STATUS_PANIC = 5
STATUS_ENTRY_DELAY = 6
STATUS_EXIT_DELAY = 7

# Alarm modes accepted by api/alarm/set_alarm.
MODE_ARM_HOME = "arm_home"
MODE_ARM_AWAY = "arm_away"
MODE_DISARM = "disarm"
MODE_PANIC = "panic"
