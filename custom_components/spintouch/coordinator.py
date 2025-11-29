"""Data coordinator for LaMotte WaterLink Spin Touch."""

from __future__ import annotations

import logging
import struct
from datetime import datetime, timedelta
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHAR_DEVICE_INFO_UUID,
    CHAR_TEST_RESULTS_UUID,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PARAMETERS,
    SPINTOUCH_SERVICE_UUID,
    TIMESTAMP_OFFSET,
)

_LOGGER = logging.getLogger(__name__)


class SpinTouchData:
    """Parsed data from SpinTouch device."""

    def __init__(self) -> None:
        """Initialize the data container."""
        self.free_chlorine: float | None = None
        self.total_chlorine: float | None = None
        self.ph: float | None = None
        self.alkalinity: float | None = None
        self.calcium_hardness: float | None = None
        self.cyanuric_acid: float | None = None
        self.salt: float | None = None
        self.iron: float | None = None
        self.phosphate: float | None = None
        self.last_test_time: datetime | None = None
        self.device_id: int | None = None
        self.firmware_version: str | None = None


class SpinTouchCoordinator(DataUpdateCoordinator[SpinTouchData]):
    """Coordinator for SpinTouch BLE device."""

    def __init__(
        self,
        hass: HomeAssistant,
        ble_device: Any,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.ble_device = ble_device
        self.entry = entry
        self._client: BleakClient | None = None
        self._address = ble_device.address

    async def _async_update_data(self) -> SpinTouchData:
        """Fetch data from SpinTouch device."""
        try:
            return await self._read_device_data()
        except BleakError as err:
            raise UpdateFailed(f"Error communicating with SpinTouch: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _read_device_data(self) -> SpinTouchData:
        """Connect and read data from the device."""
        data = SpinTouchData()

        client = await establish_connection(
            BleakClient,
            self.ble_device,
            self._address,
        )

        try:
            # Read test results characteristic
            test_results = await client.read_gatt_char(CHAR_TEST_RESULTS_UUID)
            self._parse_test_results(test_results, data)

            # Read device info characteristic
            try:
                device_info = await client.read_gatt_char(CHAR_DEVICE_INFO_UUID)
                self._parse_device_info(device_info, data)
            except BleakError:
                _LOGGER.debug("Could not read device info characteristic")

        finally:
            await client.disconnect()

        return data

    def _parse_test_results(self, raw_data: bytes, data: SpinTouchData) -> None:
        """Parse the test results from raw BLE data.

        Data format:
        - Bytes 0-3: Header
        - Bytes 4+: 6-byte entries [param_id, flags, float32_le]
        - Bytes 74-79: Timestamp (YY-MM-DD-HH-MM-SS BCD)
        """
        if len(raw_data) < 70:
            _LOGGER.warning("Test results data too short: %d bytes", len(raw_data))
            return

        _LOGGER.debug("Parsing %d bytes of test results", len(raw_data))

        # Parse each parameter
        for param_id, (offset, key, name, unit, icon, decimals) in PARAMETERS.items():
            if offset + 6 <= len(raw_data):
                # Verify param_id matches expected
                actual_id = raw_data[offset]
                if actual_id != param_id:
                    _LOGGER.debug(
                        "Param ID mismatch at offset %d: expected 0x%02X, got 0x%02X",
                        offset,
                        param_id,
                        actual_id,
                    )

                # Parse float value (little-endian, offset + 2)
                try:
                    value = struct.unpack("<f", raw_data[offset + 2 : offset + 6])[0]
                    setattr(data, key, value)
                    _LOGGER.debug("%s: %.3f %s", name, value, unit or "")
                except struct.error as err:
                    _LOGGER.debug("Error parsing %s: %s", name, err)

        # Parse timestamp (BCD format: YY-MM-DD-HH-MM-SS)
        if len(raw_data) >= TIMESTAMP_OFFSET + 6:
            try:
                year = 2000 + raw_data[TIMESTAMP_OFFSET]
                month = raw_data[TIMESTAMP_OFFSET + 1]
                day = raw_data[TIMESTAMP_OFFSET + 2]
                hour = raw_data[TIMESTAMP_OFFSET + 3]
                minute = raw_data[TIMESTAMP_OFFSET + 4]
                second = raw_data[TIMESTAMP_OFFSET + 5]

                if 1 <= month <= 12 and 1 <= day <= 31:
                    data.last_test_time = datetime(
                        year, month, day, hour, minute, second
                    )
                    _LOGGER.debug("Last test time: %s", data.last_test_time)
            except (ValueError, IndexError) as err:
                _LOGGER.debug("Error parsing timestamp: %s", err)

    def _parse_device_info(self, raw_data: bytes, data: SpinTouchData) -> None:
        """Parse device info from raw BLE data."""
        if len(raw_data) < 6:
            return

        # Device ID (little-endian uint16 at offset 0)
        data.device_id = struct.unpack("<H", raw_data[0:2])[0]

        # Firmware version (bytes 4-5)
        if len(raw_data) >= 6:
            data.firmware_version = f"{raw_data[4]}.{raw_data[5]}"

        _LOGGER.debug(
            "Device ID: %d, Firmware: %s", data.device_id, data.firmware_version
        )

    async def async_disconnect(self) -> None:
        """Disconnect from the device."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            self._client = None
