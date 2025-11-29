"""Data coordinator for LaMotte WaterLink Spin Touch."""

from __future__ import annotations

import asyncio
import logging
import struct
from datetime import datetime
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CHAR_STATUS_UUID,
    CHAR_TEST_RESULTS_UUID,
    DEVICE_NAME_PREFIX,
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
        self.connected: bool = False


class SpinTouchCoordinator(DataUpdateCoordinator[SpinTouchData]):
    """Coordinator that listens for SpinTouch and receives data when device connects."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # No polling - we wait for device to appear
        )
        self._address = address.upper()
        self.entry = entry
        self._cancel_bluetooth_callback: callable | None = None
        self._connecting = False
        self._last_data = SpinTouchData()

    async def _async_update_data(self) -> SpinTouchData:
        """Return the last received data."""
        return self._last_data

    async def async_config_entry_first_refresh(self) -> None:
        """Start listening for the device."""
        await super().async_config_entry_first_refresh()

        # Register callback for when SpinTouch is discovered via Bluetooth
        self._cancel_bluetooth_callback = bluetooth.async_register_callback(
            self.hass,
            self._on_bluetooth_event,
            BluetoothCallbackMatcher(
                connectable=True,
                service_uuids=[SPINTOUCH_SERVICE_UUID],
            ),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )

        _LOGGER.info(
            "SpinTouch listener started for %s - waiting for device to advertise",
            self._address,
        )

    @callback
    def _on_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        """Handle Bluetooth advertisement from SpinTouch."""
        # Check if this is our device (by name or address)
        if not service_info.name or not service_info.name.startswith(DEVICE_NAME_PREFIX):
            # Also check by MAC address
            if self._address not in service_info.address.upper():
                return

        _LOGGER.info(
            "SpinTouch detected: %s (%s) RSSI: %s",
            service_info.name,
            service_info.address,
            service_info.rssi,
        )

        # Don't reconnect if already connecting
        if self._connecting:
            return

        # Schedule connection (can't await in callback)
        self.hass.async_create_task(
            self._connect_and_receive(service_info),
            name=f"spintouch_connect_{service_info.address}",
        )

    async def _connect_and_receive(
        self, service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Connect to SpinTouch and receive data."""
        if self._connecting:
            return

        self._connecting = True
        _LOGGER.info("Connecting to SpinTouch %s...", service_info.name)

        try:
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, service_info.address, connectable=True
            )

            if not ble_device:
                _LOGGER.warning("Could not get BLE device for %s", service_info.address)
                return

            client = await establish_connection(
                BleakClient,
                ble_device,
                service_info.address,
                max_attempts=3,
            )

            try:
                _LOGGER.info("Connected to SpinTouch!")
                self._last_data.connected = True

                # Subscribe to status notifications
                try:
                    await client.start_notify(
                        CHAR_STATUS_UUID,
                        self._on_status_notification,
                    )
                except BleakError:
                    _LOGGER.debug("Could not subscribe to status notifications")

                # Read test results
                await self._read_test_results(client)

                # Keep connection briefly for any additional data
                await asyncio.sleep(3)

            finally:
                await client.disconnect()

        except BleakError as err:
            _LOGGER.warning("BLE error connecting to SpinTouch: %s", err)
        except Exception as err:
            _LOGGER.error("Error connecting to SpinTouch: %s", err)
        finally:
            self._connecting = False
            self._last_data.connected = False

    def _on_status_notification(self, sender, data: bytearray) -> None:
        """Handle status notifications from SpinTouch."""
        if data:
            status = data[0]
            status_names = {
                0x01: "Initializing",
                0x02: "Ready",
                0x03: "Testing",
                0x04: "Complete",
                0x05: "Error",
                0x06: "Idle",
            }
            _LOGGER.debug(
                "SpinTouch status: %s", status_names.get(status, f"0x{status:02X}")
            )

    async def _read_test_results(self, client: BleakClient) -> None:
        """Read and parse test results from the device."""
        try:
            raw_data = await client.read_gatt_char(CHAR_TEST_RESULTS_UUID)
            _LOGGER.debug("Received %d bytes of test data", len(raw_data))
            self._parse_test_results(raw_data)
            # Notify HA that we have new data
            self.async_set_updated_data(self._last_data)
        except BleakError as err:
            _LOGGER.warning("Failed to read test results: %s", err)

    def _parse_test_results(self, raw_data: bytes) -> None:
        """Parse the test results from raw BLE data."""
        if len(raw_data) < 70:
            _LOGGER.warning("Test results data too short: %d bytes", len(raw_data))
            return

        _LOGGER.debug("Parsing %d bytes of test results", len(raw_data))

        # Parse each parameter (6 bytes each: param_id, flags, float32_le)
        for param_id, (offset, key, name, unit, icon, decimals) in PARAMETERS.items():
            if offset + 6 <= len(raw_data):
                try:
                    value = struct.unpack("<f", raw_data[offset + 2 : offset + 6])[0]
                    # Validate value is reasonable
                    if -1000 < value < 100000:
                        setattr(self._last_data, key, round(value, decimals))
                        _LOGGER.info("%s: %.2f %s", name, value, unit or "")
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
                    self._last_data.last_test_time = datetime(
                        year, month, day, hour, minute, second
                    )
                    _LOGGER.info("Test time: %s", self._last_data.last_test_time)
            except (ValueError, IndexError) as err:
                _LOGGER.debug("Error parsing timestamp: %s", err)

    async def async_disconnect(self) -> None:
        """Stop listening and clean up."""
        if self._cancel_bluetooth_callback:
            self._cancel_bluetooth_callback()
            self._cancel_bluetooth_callback = None

        _LOGGER.info("SpinTouch coordinator stopped")
