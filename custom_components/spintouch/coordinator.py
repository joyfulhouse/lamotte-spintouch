"""DataUpdateCoordinator for SpinTouch BLE device."""

from __future__ import annotations

import asyncio
import logging
import struct
from datetime import datetime, timedelta
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DATA_CHARACTERISTIC_UUID,
    DISCONNECT_DELAY,
    DOMAIN,
    SENSORS,
    SERVICE_UUID,
    STATUS_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)

# Minimum data size for valid reading
MIN_DATA_SIZE = 70


class SpinTouchData:
    """Container for SpinTouch sensor data."""

    def __init__(self) -> None:
        """Initialize data container."""
        self.values: dict[str, float | None] = {}
        self.last_reading_time: datetime | None = None
        self.connected: bool = False

    def update_from_bytes(self, data: bytes) -> bool:
        """Parse BLE data and update values.

        Returns True if data was valid and parsed successfully.
        """
        if len(data) < MIN_DATA_SIZE:
            _LOGGER.warning("Data too short: %d bytes", len(data))
            return False

        _LOGGER.debug("Parsing %d bytes of SpinTouch data", len(data))

        for sensor in SENSORS:
            try:
                # Extract float32 little-endian from offset
                value = struct.unpack_from("<f", data, sensor.offset)[0]

                # Validate the value
                if (
                    value is not None
                    and not (value != value)  # NaN check
                    and sensor.min_valid <= value <= sensor.max_valid
                ):
                    self.values[sensor.key] = round(value, sensor.decimals)
                    _LOGGER.debug(
                        "%s: %.2f %s",
                        sensor.name,
                        value,
                        sensor.unit or "",
                    )
                else:
                    _LOGGER.warning(
                        "Invalid %s value: %s (valid range: %s-%s)",
                        sensor.name,
                        value,
                        sensor.min_valid,
                        sensor.max_valid,
                    )
            except struct.error as err:
                _LOGGER.error("Failed to parse %s: %s", sensor.name, err)

        # Calculate derived values
        fc = self.values.get("free_chlorine")
        tc = self.values.get("total_chlorine")
        cya = self.values.get("cyanuric_acid")

        if fc is not None and tc is not None:
            cc = tc - fc
            self.values["combined_chlorine"] = round(max(0, cc), 2)

        if fc is not None and cya is not None and cya > 0:
            self.values["fc_cya_ratio"] = round((fc / cya) * 100, 1)

        self.last_reading_time = datetime.now()
        return True


class SpinTouchCoordinator(DataUpdateCoordinator[SpinTouchData]):
    """Coordinator for SpinTouch BLE device."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        service_info: BluetoothServiceInfoBleak | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Don't poll - we use push notifications from the device
            update_interval=None,
        )
        self.address = address
        self._service_info = service_info
        self._client: BleakClient | None = None
        self._data = SpinTouchData()
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._expected_disconnect = False
        self._connect_lock = asyncio.Lock()

    @property
    def device_name(self) -> str:
        """Return the device name."""
        if self._service_info and self._service_info.name:
            return self._service_info.name
        return f"SpinTouch {self.address[-8:].replace(':', '')}"

    async def _async_update_data(self) -> SpinTouchData:
        """Fetch data - called by coordinator on demand."""
        return self._data

    async def async_connect(self) -> bool:
        """Connect to the SpinTouch device."""
        async with self._connect_lock:
            if self._client and self._client.is_connected:
                _LOGGER.debug("Already connected to %s", self.address)
                return True

            try:
                _LOGGER.info("Connecting to SpinTouch at %s", self.address)

                device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if not device:
                    _LOGGER.warning("Device %s not found", self.address)
                    return False

                self._expected_disconnect = False
                self._client = await establish_connection(
                    BleakClient,
                    device,
                    self.address,
                    disconnected_callback=self._on_disconnect,
                )

                # Subscribe to status notifications
                await self._client.start_notify(
                    STATUS_CHARACTERISTIC_UUID,
                    self._on_status_notification,
                )

                self._data.connected = True
                _LOGGER.info("Connected to SpinTouch at %s", self.address)
                self.async_update_listeners()
                return True

            except BleakError as err:
                _LOGGER.error("Failed to connect to %s: %s", self.address, err)
                self._data.connected = False
                return False
            except Exception as err:
                _LOGGER.exception("Unexpected error connecting to %s: %s", self.address, err)
                self._data.connected = False
                return False

    async def async_disconnect(self) -> None:
        """Disconnect from the SpinTouch device."""
        self._cancel_disconnect_timer()
        self._expected_disconnect = True

        if self._client and self._client.is_connected:
            try:
                _LOGGER.info("Disconnecting from SpinTouch at %s", self.address)
                await self._client.disconnect()
            except BleakError as err:
                _LOGGER.warning("Error disconnecting: %s", err)

        self._client = None
        self._data.connected = False
        self.async_update_listeners()

    @callback
    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle disconnection."""
        _LOGGER.info(
            "Disconnected from SpinTouch at %s (expected: %s)",
            self.address,
            self._expected_disconnect,
        )
        self._client = None
        self._data.connected = False
        self.async_update_listeners()

    def _on_status_notification(
        self, sender: int, data: bytearray
    ) -> None:
        """Handle status notification from SpinTouch."""
        _LOGGER.debug("Status notification received, reading data...")
        # Schedule data read on the event loop
        self.hass.async_create_task(self._async_read_data())

    async def _async_read_data(self) -> None:
        """Read data from the SpinTouch device."""
        if not self._client or not self._client.is_connected:
            _LOGGER.warning("Cannot read data - not connected")
            return

        try:
            data = await self._client.read_gatt_char(DATA_CHARACTERISTIC_UUID)
            _LOGGER.debug("Received %d bytes from SpinTouch", len(data))

            if self._data.update_from_bytes(bytes(data)):
                _LOGGER.info(
                    "SpinTouch reading: FC=%.2f TC=%.2f pH=%.2f Alk=%.0f Ca=%.0f CYA=%.0f",
                    self._data.values.get("free_chlorine", 0),
                    self._data.values.get("total_chlorine", 0),
                    self._data.values.get("ph", 0),
                    self._data.values.get("alkalinity", 0),
                    self._data.values.get("calcium", 0),
                    self._data.values.get("cyanuric_acid", 0),
                )
                self.async_set_updated_data(self._data)
                self._schedule_disconnect()

        except BleakError as err:
            _LOGGER.error("Failed to read data: %s", err)

    def _schedule_disconnect(self) -> None:
        """Schedule disconnect after delay to allow phone app access."""
        self._cancel_disconnect_timer()

        @callback
        def _disconnect_callback() -> None:
            _LOGGER.info(
                "Disconnecting after %ds to allow phone app access",
                DISCONNECT_DELAY,
            )
            self.hass.async_create_task(self.async_disconnect())

        self._disconnect_timer = self.hass.loop.call_later(
            DISCONNECT_DELAY, _disconnect_callback
        )

    def _cancel_disconnect_timer(self) -> None:
        """Cancel the disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None

    @callback
    def async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle Bluetooth event - device advertisement received."""
        _LOGGER.debug(
            "Bluetooth event for %s: %s (RSSI: %s)",
            self.address,
            change,
            service_info.rssi,
        )
        self._service_info = service_info

        # Auto-connect when device is seen
        if not self._data.connected and not self._connect_lock.locked():
            self.hass.async_create_task(self.async_connect())
