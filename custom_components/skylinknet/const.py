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

# The special device id that represents the hub's own alarm state.
HUB_DEV_ID = "F0000000"

# How often (seconds) we poll the cloud for the current alarm state.
DEFAULT_SCAN_INTERVAL = 20

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
