"""Tests for SpinTouch coordinator and data parsing."""

from __future__ import annotations

import struct

from custom_components.spintouch.const import (
    END_SIGNATURE,
    START_SIGNATURE,
)
from custom_components.spintouch.coordinator import SpinTouchData


class TestSpinTouchData:
    """Test the SpinTouchData class."""

    def test_init(self) -> None:
        """Test SpinTouchData initialization."""
        data = SpinTouchData()

        assert data.values == {}
        assert data.last_reading_time is None
        assert data.report_time is None
        assert data.connected is False
        assert data.connection_enabled is True
        assert data.detected_param_ids == set()
        assert data.num_valid_results == 0
        assert data.disk_type is None
        assert data.sanitizer_type is None

    def test_update_from_bytes_valid_data(self) -> None:
        """Test parsing valid BLE data."""
        data = SpinTouchData()

        # Build valid test data
        ble_data = build_test_ble_data(
            free_chlorine=2.5,
            ph=7.4,
            alkalinity=100.0,
            calcium=250.0,
            cyanuric_acid=40.0,
        )

        result = data.update_from_bytes(ble_data)

        assert result is True
        assert "free_chlorine" in data.values
        assert abs(data.values["free_chlorine"] - 2.5) < 0.1
        assert "ph" in data.values
        assert abs(data.values["ph"] - 7.4) < 0.1
        assert "alkalinity" in data.values
        assert abs(data.values["alkalinity"] - 100.0) < 1.0
        assert "calcium" in data.values
        assert abs(data.values["calcium"] - 250.0) < 1.0
        assert "cyanuric_acid" in data.values
        assert abs(data.values["cyanuric_acid"] - 40.0) < 1.0

    def test_update_from_bytes_too_short(self) -> None:
        """Test parsing rejects data that is too short."""
        data = SpinTouchData()

        # Only 10 bytes - way too short
        short_data = bytes([0x01, 0x02, 0x03, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

        result = data.update_from_bytes(short_data)

        assert result is False
        assert data.values == {}

    def test_update_from_bytes_invalid_signature(self) -> None:
        """Test parsing rejects invalid start signature."""
        data = SpinTouchData()

        # Wrong start signature
        bad_data = bytes([0xFF, 0xFF, 0xFF, 0xFF] + [0x00] * 87)

        result = data.update_from_bytes(bad_data)

        assert result is False

    def test_update_from_bytes_duplicate_timestamp(self) -> None:
        """Test parsing returns False for unchanged timestamp."""
        data = SpinTouchData()

        ble_data = build_test_ble_data(free_chlorine=2.5, ph=7.4)

        # First parse should succeed
        result1 = data.update_from_bytes(ble_data)
        assert result1 is True

        # Second parse with same data should return False (no new data)
        result2 = data.update_from_bytes(ble_data)
        assert result2 is False

    def test_calculated_combined_chlorine(self) -> None:
        """Test combined chlorine calculation."""
        data = SpinTouchData()

        ble_data = build_test_ble_data(
            free_chlorine=2.0,
            total_chlorine=2.5,
            ph=7.4,
        )

        result = data.update_from_bytes(ble_data)

        assert result is True
        assert "combined_chlorine" in data.values
        assert abs(data.values["combined_chlorine"] - 0.5) < 0.1

    def test_calculated_fc_cya_ratio(self) -> None:
        """Test FC/CYA ratio calculation."""
        data = SpinTouchData()

        ble_data = build_test_ble_data(
            free_chlorine=4.0,
            cyanuric_acid=50.0,
            ph=7.4,
        )

        result = data.update_from_bytes(ble_data)

        assert result is True
        assert "fc_cya_ratio" in data.values
        # FC/CYA = 4/50 * 100 = 8%
        assert abs(data.values["fc_cya_ratio"] - 8.0) < 0.5

    def test_detected_disk_series_chlorine(self) -> None:
        """Test disk series detection for chlorine disk."""
        data = SpinTouchData()

        ble_data = build_test_ble_data(
            free_chlorine=2.5,
            total_chlorine=2.5,
            ph=7.4,
        )

        data.update_from_bytes(ble_data)

        # Should detect as 303 (chlorine disk)
        assert data.detected_disk_series == "303"

    def test_detected_disk_series_bromine(self) -> None:
        """Test disk series detection for bromine disk."""
        data = SpinTouchData()

        # Build data with bromine instead of chlorine
        ble_data = build_test_ble_data(
            bromine=5.0,
            ph=7.4,
        )

        data.update_from_bytes(ble_data)

        # Should detect as 203 (bromine disk)
        assert data.detected_disk_series == "203"

    def test_metadata_parsing(self) -> None:
        """Test metadata parsing from BLE data."""
        data = SpinTouchData()

        ble_data = build_test_ble_data(
            free_chlorine=2.5,
            ph=7.4,
            num_valid=5,
            disk_type_idx=18,  # 303
            sanitizer_idx=0,  # Chlorine
        )

        data.update_from_bytes(ble_data)

        assert data.num_valid_results == 5
        assert data.disk_type_index == 18
        assert data.disk_type == "303"
        assert data.sanitizer_type_index == 0
        assert data.sanitizer_type == "Chlorine"

    def test_timestamp_parsing(self) -> None:
        """Test timestamp parsing from BLE data."""
        data = SpinTouchData()

        ble_data = build_test_ble_data(
            free_chlorine=2.5,
            ph=7.4,
            year=25,  # 2025
            month=11,
            day=29,
            hour=14,
            minute=30,
            second=45,
        )

        data.update_from_bytes(ble_data)

        assert data.report_time is not None
        assert data.report_time.year == 2025
        assert data.report_time.month == 11
        assert data.report_time.day == 29

    def test_invalid_value_filtering(self) -> None:
        """Test that invalid values are filtered out."""
        data = SpinTouchData()

        # Build data with invalid pH (out of range 0-14)
        ble_data = build_test_ble_data(
            free_chlorine=2.5,
            ph=99.0,  # Invalid
        )

        data.update_from_bytes(ble_data)

        assert "free_chlorine" in data.values
        assert "ph" not in data.values  # Should be filtered


def build_test_ble_data(
    free_chlorine: float | None = None,
    total_chlorine: float | None = None,
    bromine: float | None = None,
    ph: float | None = None,
    alkalinity: float | None = None,
    calcium: float | None = None,
    cyanuric_acid: float | None = None,
    copper: float | None = None,
    iron: float | None = None,
    borate: float | None = None,
    salt: float | None = None,
    year: int = 25,
    month: int = 11,
    day: int = 29,
    hour: int = 12,
    minute: int = 30,
    second: int = 45,
    ampm: int = 0,
    military: int = 1,
    num_valid: int = 10,
    disk_type_idx: int = 18,
    sanitizer_idx: int = 0,
) -> bytes:
    """Build a test BLE data packet."""
    # Start with signature
    data = bytearray(START_SIGNATURE)

    # Map parameter names to (param_id, decimals, value)
    param_mapping: dict[str, tuple[int, int, float | None]] = {
        "free_chlorine": (0x01, 2, free_chlorine),
        "total_chlorine": (0x02, 2, total_chlorine),
        "bromine": (0x03, 2, bromine),
        "ph": (0x06, 1, ph),
        "alkalinity": (0x07, 0, alkalinity),
        "calcium": (0x0F, 0, calcium),
        "cyanuric_acid": (0x0A, 0, cyanuric_acid),
        "copper": (0x0C, 2, copper),
        "iron": (0x0B, 2, iron),
        "borate": (0x0D, 1, borate),
        "salt": (0x10, 0, salt),
    }

    # Build entries list from non-None values
    entries: list[tuple[int, int, float]] = [
        (param_id, decimals, value)
        for param_id, decimals, value in param_mapping.values()
        if value is not None
    ]

    # Pad to 12 entries
    while len(entries) < 12:
        entries.append((0x00, 0, 0.0))

    for test_type, decimals, value in entries:
        data.append(test_type)
        data.append(decimals)
        data.extend(struct.pack("<f", value))

    # Timestamp (8 bytes)
    data.extend([year, month, day, hour, minute, second, ampm, military])

    # Metadata (3 bytes)
    data.extend([num_valid, disk_type_idx, sanitizer_idx])

    # End signature
    data.extend(END_SIGNATURE)

    return bytes(data)


class TestDataValidation:
    """Test data validation functions."""

    def test_valid_timestamp_range(self) -> None:
        """Test timestamp validation accepts valid dates."""
        assert SpinTouchData._is_valid_timestamp(2025, 11, 29, 12, 30, 45)
        assert SpinTouchData._is_valid_timestamp(2020, 1, 1, 0, 0, 0)
        assert SpinTouchData._is_valid_timestamp(2099, 12, 31, 23, 59, 59)

    def test_invalid_timestamp_year(self) -> None:
        """Test timestamp validation rejects invalid year."""
        assert not SpinTouchData._is_valid_timestamp(2019, 11, 29, 12, 30, 45)
        assert not SpinTouchData._is_valid_timestamp(2100, 11, 29, 12, 30, 45)

    def test_invalid_timestamp_month(self) -> None:
        """Test timestamp validation rejects invalid month."""
        assert not SpinTouchData._is_valid_timestamp(2025, 0, 29, 12, 30, 45)
        assert not SpinTouchData._is_valid_timestamp(2025, 13, 29, 12, 30, 45)

    def test_invalid_timestamp_day(self) -> None:
        """Test timestamp validation rejects invalid day."""
        assert not SpinTouchData._is_valid_timestamp(2025, 11, 0, 12, 30, 45)
        assert not SpinTouchData._is_valid_timestamp(2025, 11, 32, 12, 30, 45)

    def test_invalid_timestamp_time(self) -> None:
        """Test timestamp validation rejects invalid time."""
        assert not SpinTouchData._is_valid_timestamp(2025, 11, 29, 24, 30, 45)
        assert not SpinTouchData._is_valid_timestamp(2025, 11, 29, 12, 60, 45)
        assert not SpinTouchData._is_valid_timestamp(2025, 11, 29, 12, 30, 60)
