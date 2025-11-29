"""Constants for the SpinTouch integration."""

from __future__ import annotations

DOMAIN = "spintouch"
MANUFACTURER = "LaMotte"
MODEL = "WaterLink Spin Touch"

# BLE Service and Characteristic UUIDs
# Discovered via nRF Connect on 2025-11-28
SPINTOUCH_SERVICE_UUID = "00000000-0000-1000-8000-bbbd00000000"
CHAR_TEST_RESULTS_UUID = "00000000-0000-1000-8000-bbbd00000010"
CHAR_STATUS_UUID = "00000000-0000-1000-8000-bbbd00000011"
CHAR_DEVICE_INFO_UUID = "00000000-0000-1000-8000-bbbd00000031"

# Device name prefix for discovery
DEVICE_NAME_PREFIX = "SpinTouch"

# Data format constants
DATA_HEADER_SIZE = 4
DATA_ENTRY_SIZE = 6  # [param_id, flags, float32_le]
TIMESTAMP_OFFSET = 74
TIMESTAMP_SIZE = 6

# Parameter IDs and their offsets in the data
# Format: param_id -> (offset, name, unit, icon, decimals)
PARAMETERS = {
    0x01: (4, "free_chlorine", "Free Chlorine", "ppm", "mdi:flask", 2),
    0x02: (10, "total_chlorine", "Total Chlorine", "ppm", "mdi:flask", 2),
    0x06: (22, "ph", "pH", None, "mdi:ph", 2),
    0x07: (28, "alkalinity", "Total Alkalinity", "ppm", "mdi:water", 1),
    0x0F: (34, "calcium_hardness", "Calcium Hardness", "ppm", "mdi:water", 1),
    0x0A: (40, "cyanuric_acid", "Cyanuric Acid", "ppm", "mdi:shield-sun", 1),
    0x0C: (46, "salt", "Salt", "ppm", "mdi:shaker", 2),
    0x0B: (52, "iron", "Iron", "ppm", "mdi:iron", 3),
    0x0D: (58, "phosphate", "Phosphate", "ppb", "mdi:leaf", 1),
}

# All parameter keys for iteration
PARAMETER_KEYS = [
    "free_chlorine",
    "total_chlorine",
    "ph",
    "alkalinity",
    "calcium_hardness",
    "cyanuric_acid",
    "salt",
    "iron",
    "phosphate",
]

# Status codes from notifications
STATUS_CODES = {
    0x01: "Initializing",
    0x02: "Ready",
    0x03: "Testing",
    0x04: "Complete",
    0x05: "Error",
    0x06: "Idle",
}

# Update interval for polling (seconds)
DEFAULT_UPDATE_INTERVAL = 60
