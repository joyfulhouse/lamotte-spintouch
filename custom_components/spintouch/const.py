"""Constants for the LaMotte SpinTouch integration.

Data format derived from decompiled WaterLinkSolutionsHome.dll (2025-11-29).
See RESEARCH.md for full protocol documentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

DOMAIN = "spintouch"

# Configuration
CONF_DISK_SERIES = "disk_series"

# Supported disk series and their param 0x0D chemical
# Per app decompilation: 0x0D = BOR (Borate), 0x0E = PHOS (Phosphate)
# However, observed BLE data suggests disk-dependent interpretation
DISK_SERIES_OPTIONS = {
    "auto": "Auto-detect",
    "203": "Phosphate",  # Bromine disk with phosphate
    "204": "Phosphate",  # High range with phosphate
    "303": "Borate",  # Chlorine disk with borate
    "304": "Borate",  # High range with borate
}
DEFAULT_DISK_SERIES = "auto"


def get_disk_series_display_options() -> dict[str, str]:
    """Get disk series options formatted for display in config flow.

    Returns a dictionary mapping series codes to human-readable labels.
    """
    return {
        series: f"Disk {series} ({chemical})" for series, chemical in DISK_SERIES_OPTIONS.items()
    }


# BLE UUIDs (from Constants class in decompiled app)
SERVICE_UUID = "00000000-0000-1000-8000-bbbd00000000"  # SPIN_TOUCH_SERVICE
DATA_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000010"  # SPIN_TOUCH_TTEST
STATUS_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000011"  # SPIN_TOUCH_TESTAVAIL
SENDTEST_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000012"  # SPIN_TOUCH_SENDTEST
ACK_CHARACTERISTIC_UUID = "00000000-0000-1000-8000-bbbd00000013"  # SPIN_TOUCH_TESTACK

# Connection settings
DISCONNECT_DELAY = 10  # seconds after reading before disconnect
RECONNECT_DELAY = 300  # seconds to wait before reconnecting (5 min)
VISIBILITY_CHECK_INTERVAL = 30  # seconds between checks when disconnected

# Data parsing constants (from TestStructure.Parse() in decompiled app)
# Total structure: 91 bytes
# [0-3] Start signature, [4-75] 12 entries, [76-83] timestamp
# [84-86] metadata, [87-90] end signature
START_SIGNATURE = bytes([0x01, 0x02, 0x03, 0x05])  # Prime numbers!
END_SIGNATURE = bytes([0x07, 0x0B, 0x0D, 0x11])  # Also primes: 7, 11, 13, 17
HEADER_SIZE = 4  # Start signature: [0x01, 0x02, 0x03, 0x05]
ENTRY_SIZE = 6  # Each entry: [TestType, Decimals, float32_le]
MAX_ENTRIES = 12  # TestResults array has 12 slots
TIMESTAMP_OFFSET = 76  # Bytes 76-83: YY-MM-DD-HH-MM-SS-AMPM-Military
TIMESTAMP_SIZE = 8  # Full timestamp including AM/PM and military flags
METADATA_OFFSET = 84  # Bytes 84-86: num_valid, disk_type, sanitizer
END_SIGNATURE_OFFSET = 87  # Bytes 87-90: end signature
MIN_DATA_SIZE = 91  # Minimum valid data size

# Disk type indices (from discStr array in decompiled app)
DISK_TYPE_MAP = {
    0: "101",
    1: "102",
    2: "201",
    3: "202",
    4: "301",
    5: "302",
    6: "401",
    7: "402",  # Biguanide
    8: "501",
    9: "601",
    16: "103",
    17: "203",  # Phosphate disk
    18: "303",  # Borate disk
    19: "503",
    20: "603",
    22: "104",
    23: "204",  # High range + Phosphate
    24: "304",  # High range + Borate
}

# Sanitizer type indices (from sanStr array in decompiled app)
SANITIZER_TYPE_MAP = {
    0: "Chlorine",
    1: "Salt",
    2: "Bromine",
    3: "Biguanide",
    4: "DWTreated",
    5: "AQFresh",
    6: "CTCL",
    7: "CTBR",
    8: "Unknown",
}


class ParamId(IntEnum):
    """Parameter IDs (TestType) in the SpinTouch BLE data.

    From testStr array in decompiled app. These are indices into
    the TestFactorCode enum which maps to chemical names.

    Different disk series include different parameters.
    Parse by scanning for these IDs, not by fixed offset.
    """

    # testStr[1] = "FCL" -> TestFactorCode.FCL
    FREE_CHLORINE = 0x01
    # testStr[2] = "TCL" -> TestFactorCode.TCL
    TOTAL_CHLORINE = 0x02
    # testStr[3] = "BR" -> TestFactorCode.BR
    BROMINE = 0x03
    # testStr[6] = "PH" -> TestFactorCode.PH
    PH = 0x06
    # testStr[7] = "ALK" -> TestFactorCode.ALK
    ALKALINITY = 0x07
    # testStr[8] = "HARDHR" -> TestFactorCode.HARD (high range)
    CALCIUM_HR = 0x08
    # testStr[10] = "CYA" -> TestFactorCode.CYA
    CYANURIC_ACID = 0x0A
    # testStr[11] = "IRON" -> TestFactorCode.IRON
    IRON = 0x0B
    # testStr[12] = "COPPER" -> TestFactorCode.COPPER
    COPPER = 0x0C
    # testStr[13] = "BOR" -> TestFactorCode.BORATE (per app)
    # However, observed as Phosphate on disk 203 - needs verification
    BORATE_0D = 0x0D
    # testStr[14] = "PHOS" -> TestFactorCode.PHOSPHATE (per app)
    # However, observed as Borate on disk 203/204 - needs verification
    PHOSPHATE_0E = 0x0E
    # testStr[15] = "CALH" -> TestFactorCode.HARDCA (calcium hardness)
    CALCIUM = 0x0F
    # testStr[16] = "SALT" -> TestFactorCode.SALT
    SALT = 0x10
    # testStr[17] = "CCL" -> TestFactorCode.CCL (combined chlorine)
    COMBINED_CHLORINE = 0x11


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
        param_ids=[ParamId.CALCIUM, ParamId.CALCIUM_HR],  # 0x0F (standard) and 0x08 (high range)
        min_valid=0,
        max_valid=1200,  # High range goes to 1200 ppm
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
    # Phosphate sensor - param 0x0E
    # Per app: testStr[14] = "PHOS" -> Phosphate
    # Unit is ppb per GenerateTestFactor() in decompiled app
    SensorDefinition(
        key="phosphate",
        name="Phosphate",
        unit="ppb",
        icon="mdi:flask-outline",
        decimals=0,
        param_ids=[ParamId.PHOSPHATE_0E],  # 0x0E
        min_valid=0,
        max_valid=2500,  # 0-2000 ppb range per LaMotte specs
    ),
    # Borate sensor - param 0x0D
    # Per app: testStr[13] = "BOR" -> Borate
    # Name may be overridden based on disk_series config if disk-dependent
    SensorDefinition(
        key="borate",
        name="Borate",
        unit="ppm",
        icon="mdi:flask-outline",
        decimals=1,
        param_ids=[ParamId.BORATE_0D],  # 0x0D
        min_valid=0,
        max_valid=100,  # 0-80 ppm range per LaMotte specs
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
