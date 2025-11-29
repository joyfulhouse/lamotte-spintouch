"""Constants for the LaMotte SpinTouch integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

DOMAIN = "spintouch"

# BLE UUIDs
SERVICE_UUID = "00000000-0000-1000-8000-bbbd00000000"
DATA_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000010"
STATUS_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000011"

# Connection settings
DISCONNECT_DELAY = 10  # seconds after reading before disconnect
RECONNECT_DELAY = 300  # seconds to wait before reconnecting (5 min)

# Data parsing - offsets into the BLE data packet
# Format: 4-byte header, then 6-byte entries [param_id, flags, float32_le]


class ParamId(IntEnum):
    """Parameter IDs in the SpinTouch BLE data."""

    FREE_CHLORINE = 0x01
    TOTAL_CHLORINE = 0x02
    PH = 0x06
    ALKALINITY = 0x07
    CYANURIC_ACID = 0x0A
    IRON = 0x0B
    SALT = 0x0C
    PHOSPHATE = 0x0D
    CALCIUM_HARDNESS = 0x0F


@dataclass
class SensorDefinition:
    """Definition for a SpinTouch sensor."""

    key: str
    name: str
    unit: str | None
    icon: str
    decimals: int
    offset: int  # Byte offset in BLE data where float value starts
    min_valid: float
    max_valid: float


# Sensor definitions with byte offsets for parsing
SENSORS: list[SensorDefinition] = [
    SensorDefinition(
        key="free_chlorine",
        name="Free Chlorine",
        unit="ppm",
        icon="mdi:flask",
        decimals=2,
        offset=6,
        min_valid=0,
        max_valid=20,
    ),
    SensorDefinition(
        key="total_chlorine",
        name="Total Chlorine",
        unit="ppm",
        icon="mdi:flask",
        decimals=2,
        offset=12,
        min_valid=0,
        max_valid=20,
    ),
    SensorDefinition(
        key="ph",
        name="pH",
        unit=None,
        icon="mdi:ph",
        decimals=2,
        offset=24,
        min_valid=0,
        max_valid=14,
    ),
    SensorDefinition(
        key="alkalinity",
        name="Total Alkalinity",
        unit="ppm",
        icon="mdi:water",
        decimals=1,
        offset=30,
        min_valid=0,
        max_valid=500,
    ),
    SensorDefinition(
        key="calcium",
        name="Calcium Hardness",
        unit="ppm",
        icon="mdi:water",
        decimals=1,
        offset=36,
        min_valid=0,
        max_valid=1000,
    ),
    SensorDefinition(
        key="cyanuric_acid",
        name="Cyanuric Acid",
        unit="ppm",
        icon="mdi:shield-sun",
        decimals=1,
        offset=42,
        min_valid=0,
        max_valid=300,
    ),
    SensorDefinition(
        key="salt",
        name="Salt",
        unit="ppm",
        icon="mdi:shaker",
        decimals=0,
        offset=48,
        min_valid=0,
        max_valid=10000,
    ),
    SensorDefinition(
        key="iron",
        name="Iron",
        unit="ppm",
        icon="mdi:iron",
        decimals=3,
        offset=54,
        min_valid=0,
        max_valid=10,
    ),
    SensorDefinition(
        key="phosphate",
        name="Phosphate",
        unit="ppb",
        icon="mdi:leaf",
        decimals=1,
        offset=60,
        min_valid=0,
        max_valid=2000,
    ),
]


@dataclass
class CalculatedSensorDefinition:
    """Definition for a calculated SpinTouch sensor."""

    key: str
    name: str
    unit: str | None
    icon: str
    decimals: int


# Calculated sensors (derived from primary sensors)
CALCULATED_SENSORS: list[CalculatedSensorDefinition] = [
    CalculatedSensorDefinition(
        key="combined_chlorine",
        name="Combined Chlorine",
        unit="ppm",
        icon="mdi:flask-outline",
        decimals=2,
    ),
    CalculatedSensorDefinition(
        key="fc_cya_ratio",
        name="FC/CYA Ratio",
        unit="%",
        icon="mdi:percent",
        decimals=1,
    ),
]
