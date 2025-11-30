"""Fixtures for SpinTouch tests."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Mock homeassistant modules before importing spintouch
# This prevents import errors from HA's transitive dependencies
mock_bluetooth = MagicMock()
mock_bluetooth.async_discovered_service_info = MagicMock(return_value=[])
mock_bluetooth.async_last_service_info = MagicMock(return_value=None)
mock_bluetooth.async_register_callback = MagicMock(return_value=lambda: None)
mock_bluetooth.BluetoothScanningMode = MagicMock()
mock_bluetooth.BluetoothScanningMode.ACTIVE = "active"
mock_bluetooth.BluetoothScanningMode.PASSIVE = "passive"

mock_bluetooth_match = MagicMock()
mock_bluetooth_match.ADDRESS = "address"
mock_bluetooth_match.BluetoothCallbackMatcher = MagicMock(return_value={})

sys.modules["homeassistant.components.bluetooth"] = mock_bluetooth
sys.modules["homeassistant.components.bluetooth.match"] = mock_bluetooth_match

# Mock bleak modules
mock_bleak = MagicMock()
sys.modules["bleak"] = mock_bleak
sys.modules["bleak_retry_connector"] = MagicMock()

# Now import spintouch modules (must be after mocking)
from custom_components.spintouch.const import SERVICE_UUID  # noqa: E402

# Enable pytest-asyncio auto mode
pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: Generator[None, None, None],  # noqa: ARG001
) -> Generator[None, None, None]:
    """Enable custom integrations in Home Assistant."""
    yield  # type: ignore[misc]


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.spintouch.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_bluetooth_fixture() -> Generator[MagicMock, None, None]:
    """Mock bluetooth discovery."""
    with patch("custom_components.spintouch.config_flow.bluetooth") as mock_bt:
        mock_bt.async_discovered_service_info.return_value = []
        yield mock_bt


@pytest.fixture
def mock_bluetooth_service_info() -> MagicMock:
    """Create a mock BluetoothServiceInfoBleak."""
    service_info = MagicMock()
    service_info.address = "BB:BD:05:0B:2D:1F"
    service_info.name = "SpinTouch-0B2D1F"
    service_info.service_uuids = [SERVICE_UUID]
    service_info.rssi = -60
    return service_info


@pytest.fixture
def mock_bleak_client() -> Generator[MagicMock, None, None]:
    """Mock BleakClient."""
    with patch("custom_components.spintouch.coordinator.BleakClient") as mock_client:
        client_instance = MagicMock()
        client_instance.is_connected = True
        client_instance.connect = AsyncMock()
        client_instance.disconnect = AsyncMock()
        client_instance.start_notify = AsyncMock()
        client_instance.read_gatt_char = AsyncMock(return_value=SAMPLE_BLE_DATA)
        client_instance.write_gatt_char = AsyncMock()
        mock_client.return_value = client_instance
        yield mock_client


# Sample BLE data from a real SpinTouch device (Chlorine 303 disk)
# Start signature + 12 entries + timestamp + metadata + end signature
SAMPLE_BLE_DATA = bytes(
    [
        # Start signature
        0x01,
        0x02,
        0x03,
        0x05,
        # Entry 1: Free Chlorine (0x01), 2 decimals, 2.50 ppm
        0x01,
        0x02,
        0x00,
        0x00,
        0x20,
        0x40,
        # Entry 2: Total Chlorine (0x02), 2 decimals, 2.75 ppm
        0x02,
        0x02,
        0x00,
        0x00,
        0x30,
        0x40,
        # Entry 3: Combined Chlorine placeholder (0x11), 2 decimals, 0.25 ppm
        0x11,
        0x02,
        0x00,
        0x00,
        0x80,
        0x3E,
        # Entry 4: pH (0x06), 1 decimal, 7.40
        0x06,
        0x01,
        0xCD,
        0xCC,
        0xEC,
        0x40,
        # Entry 5: Alkalinity (0x07), 0 decimals, 100 ppm
        0x07,
        0x00,
        0x00,
        0x00,
        0xC8,
        0x42,
        # Entry 6: Calcium (0x0F), 0 decimals, 250 ppm
        0x0F,
        0x00,
        0x00,
        0x00,
        0x7A,
        0x43,
        # Entry 7: Cyanuric Acid (0x0A), 0 decimals, 40 ppm
        0x0A,
        0x00,
        0x00,
        0x00,
        0x20,
        0x42,
        # Entry 8: Copper (0x0C), 2 decimals, 0.10 ppm
        0x0C,
        0x02,
        0xCD,
        0xCC,
        0xCC,
        0x3D,
        # Entry 9: Iron (0x0B), 2 decimals, 0.05 ppm
        0x0B,
        0x02,
        0xCD,
        0xCC,
        0x4C,
        0x3D,
        # Entry 10: Borate (0x0D), 1 decimal, 30.0 ppm
        0x0D,
        0x01,
        0x00,
        0x00,
        0xF0,
        0x41,
        # Entry 11: Salt (0x10), 0 decimals, 3000 ppm
        0x10,
        0x00,
        0x00,
        0x80,
        0x3B,
        0x45,
        # Entry 12: Empty
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        # Timestamp: 2025-11-29 12:30:45
        0x19,
        0x0B,
        0x1D,
        0x0C,
        0x1E,
        0x2D,
        0x00,
        0x01,
        # Metadata: 10 valid results, disk type 18 (303), sanitizer 0 (Chlorine)
        0x0A,
        0x12,
        0x00,
        # End signature
        0x07,
        0x0B,
        0x0D,
        0x11,
    ]
)


def get_config_entry_data() -> dict[str, Any]:
    """Return mock config entry data."""
    return {
        "address": "BB:BD:05:0B:2D:1F",
        "disk_series": "auto",
    }
