"""Constants for the LaMotte SpinTouch integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

DOMAIN = "spintouch"

# Configuration
CONF_DISK_SERIES = "disk_series"

# Supported disk series and their param 0x0D chemical
# 0x0D is overloaded - means Phosphate on some disks, Borate on others
DISK_SERIES_OPTIONS = {
    "203": "Phosphate",
    "204": "Borate",
    "303": "Borate",
    "304": "Borate",
}
DEFAULT_DISK_SERIES = "303"

# BLE UUIDs
SERVICE_UUID = "00000000-0000-1000-8000-bbbd00000000"
DATA_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000010"
STATUS_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000011"

# Connection settings
DISCONNECT_DELAY = 10  # seconds after reading before disconnect
RECONNECT_DELAY = 300  # seconds to wait before reconnecting (5 min)

# Data parsing constants
HEADER_SIZE = 4  # First 4 bytes are header
ENTRY_SIZE = 6  # Each parameter entry is 6 bytes [param_id, flags, float32_le]
MAX_ENTRIES = 11  # Maximum number of parameter entries
TIMESTAMP_OFFSET = 76  # Bytes 76-81: YY-MM-DD-HH-MM-SS


class ParamId(IntEnum):
    """Parameter IDs in the SpinTouch BLE data.

    Different disk series include different parameters.
    Parse by scanning for these IDs, not by fixed offset.
    """

    FREE_CHLORINE = 0x01  # Chlorine disks (303, 304)
    TOTAL_CHLORINE = 0x02  # Chlorine disks (303, 304)
    BROMINE = 0x03  # Bromine disks (203)
    PH = 0x06
    ALKALINITY = 0x07
    CALCIUM_204 = 0x08  # Calcium Hardness on disk 204
    CYANURIC_ACID = 0x0A
    IRON = 0x0B  # Chlorine/Bromine disks (203, 303, 304)
    COPPER = 0x0C  # All disks
    PHOSPHATE_BORATE = 0x0D  # Phosphate (disk 203) or Borate (disk 303/304) - context-dependent
    BORATE = 0x0E  # Borate on disk 203, 204
    CALCIUM = 0x0F  # Calcium Hardness on disk 203, 303, 304
    SALT = 0x10  # All disks
    UNKNOWN_11 = 0x11


@dataclass
class SensorDefinition:
    """Definition for a SpinTouch sensor."""

    key: str  # Unique sensor key (e.g., "free_chlorine")
    name: str  # Display name (e.g., "Free Chlorine")
    unit: str | None  # Unit of measurement
    icon: str  # MDI icon
    decimals: int  # Decimal places for display
    param_ids: list[int]  # List of param_ids that map to this sensor
    min_valid: float  # Minimum valid value
    max_valid: float  # Maximum valid value


# Sensor definitions mapped by param_id
# Multiple param_ids can map to the same logical sensor (e.g., Calcium: 0x08 and 0x0F)
SENSORS: list[SensorDefinition] = [
    SensorDefinition(
        key="free_chlorine",
        name="Free Chlorine",
        unit="ppm",
        icon="mdi:flask",
        decimals=2,
        param_ids=[ParamId.FREE_CHLORINE],
        min_valid=0,
        max_valid=20,
    ),
    SensorDefinition(
        key="total_chlorine",
        name="Total Chlorine",
        unit="ppm",
        icon="mdi:flask",
        decimals=2,
        param_ids=[ParamId.TOTAL_CHLORINE],
        min_valid=0,
        max_valid=20,
    ),
    SensorDefinition(
        key="bromine",
        name="Bromine",
        unit="ppm",
        icon="mdi:flask",
        decimals=2,
        param_ids=[ParamId.BROMINE],
        min_valid=0,
        max_valid=20,
    ),
    SensorDefinition(
        key="ph",
        name="pH",
        unit=None,
        icon="mdi:ph",
        decimals=2,
        param_ids=[ParamId.PH],
        min_valid=0,
        max_valid=14,
    ),
    SensorDefinition(
        key="alkalinity",
        name="Total Alkalinity",
        unit="ppm",
        icon="mdi:water",
        decimals=1,
        param_ids=[ParamId.ALKALINITY],
        min_valid=0,
        max_valid=500,
    ),
    SensorDefinition(
        key="calcium",
        name="Calcium Hardness",
        unit="ppm",
        icon="mdi:water",
        decimals=1,
        param_ids=[ParamId.CALCIUM, ParamId.CALCIUM_204],  # Both 0x0F and 0x08
        min_valid=0,
        max_valid=1000,
    ),
    SensorDefinition(
        key="cyanuric_acid",
        name="Cyanuric Acid",
        unit="ppm",
        icon="mdi:shield-sun",
        decimals=1,
        param_ids=[ParamId.CYANURIC_ACID],
        min_valid=0,
        max_valid=300,
    ),
    SensorDefinition(
        key="salt",
        name="Salt",
        unit="ppm",
        icon="mdi:shaker",
        decimals=0,
        param_ids=[ParamId.SALT],  # 0x10
        min_valid=0,
        max_valid=10000,
    ),
    SensorDefinition(
        key="copper",
        name="Copper",
        unit="ppm",
        icon="mdi:flask",
        decimals=2,
        param_ids=[ParamId.COPPER],  # 0x0C
        min_valid=0,
        max_valid=5,
    ),
    SensorDefinition(
        key="iron",
        name="Iron",
        unit="ppm",
        icon="mdi:iron",
        decimals=2,
        param_ids=[ParamId.IRON],  # 0x0B
        min_valid=0,
        max_valid=5,
    ),
    # Borate sensor - uses 0x0E (disk 204) or 0x0D (disk 303 when configured as Borate)
    SensorDefinition(
        key="borate",
        name="Borate",
        unit="ppm",
        icon="mdi:flask-outline",
        decimals=1,
        param_ids=[ParamId.BORATE],  # 0x0E - always Borate
        min_valid=0,
        max_valid=200,
    ),
    # Phosphate/Borate sensor - param 0x0D, meaning depends on disk series
    # Name is overridden based on disk_series config
    SensorDefinition(
        key="param_0d",
        name="Borate",  # Default name, overridden based on disk_series config
        unit="ppm",
        icon="mdi:flask-outline",
        decimals=1,
        param_ids=[ParamId.PHOSPHATE_BORATE],  # 0x0D - context-dependent
        min_valid=0,
        max_valid=2000,
    ),
]


# Build lookup table: param_id -> sensor definition
def _build_param_id_to_sensor() -> dict[int, SensorDefinition]:
    """Build a lookup table from param_id to sensor definition."""
    lookup: dict[int, SensorDefinition] = {}
    for sensor in SENSORS:
        for param_id in sensor.param_ids:
            lookup[param_id] = sensor
    return lookup


PARAM_ID_TO_SENSOR: dict[int, SensorDefinition] = _build_param_id_to_sensor()


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
