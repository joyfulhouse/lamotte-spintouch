"""DataUpdateCoordinator for SpinTouch BLE device."""

from __future__ import annotations

import asyncio
import datetime as dt_module
import logging
import math
import struct
from typing import TYPE_CHECKING

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from .const import (
    DATA_CHARACTERISTIC_UUID,
    DISCONNECT_DELAY,
    DOMAIN,
    RECONNECT_DELAY,
    SENSORS,
    STATUS_CHARACTERISTIC_UUID,
    TIMESTAMP_OFFSET,
)

_LOGGER = logging.getLogger(__name__)

# Minimum data size for valid reading (need at least 82 bytes for timestamp)
MIN_DATA_SIZE = 82


class SpinTouchData:
    """Container for SpinTouch sensor data."""

    def __init__(self) -> None:
        """Initialize data container."""
        self.values: dict[str, float | None] = {}
        self.last_reading_time: datetime | None = None
        self.report_time: datetime | None = None  # Timestamp from SpinTouch report
        self.connected: bool = False
        self.connection_enabled: bool = True

    def update_from_bytes(self, data: bytes) -> bool:
        """Parse BLE data and update values.

        Returns True if data was valid AND represents a new report (different timestamp).
        """
        if len(data) < MIN_DATA_SIZE:
            _LOGGER.warning("Data too short: %d bytes", len(data))
            return False

        _LOGGER.debug("Parsing %d bytes of SpinTouch data", len(data))

        # Parse report timestamp first to check if this is new data
        old_report_time = self.report_time
        self._parse_report_timestamp(data)

        # If report timestamp hasn't changed, this is the same data - skip update
        if old_report_time is not None and self.report_time == old_report_time:
            _LOGGER.debug("Report timestamp unchanged, skipping update")
            return False

        for sensor in SENSORS:
            try:
                # Extract float32 little-endian from offset
                value = struct.unpack_from("<f", data, sensor.offset)[0]

                # Validate the value
                if (
                    value is not None
                    and not math.isnan(value)
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

        self.last_reading_time = dt_util.utcnow()
        return True

    def _parse_report_timestamp(self, data: bytes) -> None:
        """Parse the report timestamp from BLE data."""
        if len(data) < TIMESTAMP_OFFSET + 6:
            _LOGGER.warning("Data too short for timestamp parsing")
            return

        try:
            year = 2000 + data[TIMESTAMP_OFFSET]
            month = data[TIMESTAMP_OFFSET + 1]
            day = data[TIMESTAMP_OFFSET + 2]
            hour = data[TIMESTAMP_OFFSET + 3]
            minute = data[TIMESTAMP_OFFSET + 4]
            second = data[TIMESTAMP_OFFSET + 5]

            # Validate all ranges at once
            if not (
                2020 <= year <= 2099
                and 1 <= month <= 12
                and 1 <= day <= 31
                and 0 <= hour <= 23
                and 0 <= minute <= 59
                and 0 <= second <= 59
            ):
                _LOGGER.warning(
                    "Invalid timestamp values: %d-%02d-%02d %02d:%02d:%02d",
                    year,
                    month,
                    day,
                    hour,
                    minute,
                    second,
                )
                return

            # Create timezone-aware datetime (assume local time from device)
            local_tz = dt_util.get_default_time_zone()
            naive_dt = dt_module.datetime(year, month, day, hour, minute, second)
            self.report_time = naive_dt.replace(tzinfo=local_tz)

            _LOGGER.debug(
                "Report timestamp: %s",
                self.report_time.isoformat(),
            )
        except (ValueError, IndexError) as err:
            _LOGGER.warning("Failed to parse report timestamp: %s", err)


class SpinTouchCoordinator(DataUpdateCoordinator[SpinTouchData]):  # type: ignore[misc]
    """Coordinator for SpinTouch BLE device.

    Connection lifecycle (mirrors ESPHome behavior):
    1. Auto-connect when device is discovered via Bluetooth advertisement
    2. Stay connected and listen for status notifications
    3. When data is received, start disconnect timer
    4. After DISCONNECT_DELAY (10s) with no new data, disconnect
    5. Stay disconnected for RECONNECT_DELAY (5 min) to allow phone app
    6. After reconnect delay, enable connection again
    7. Will reconnect when next Bluetooth advertisement is seen
    """

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

        # Connection lifecycle timers
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._reconnect_timer: asyncio.TimerHandle | None = None

        # Connection state flags
        self._expected_disconnect = False
        self._stay_disconnected = False  # True during reconnect delay period
        self._reading_received = False  # Reset by disconnect timer
        self._connect_lock = asyncio.Lock()

    @property
    def device_name(self) -> str:
        """Return the device name."""
        if self._service_info and self._service_info.name:
            return str(self._service_info.name)
        return f"SpinTouch {self.address[-8:].replace(':', '')}"

    async def _async_update_data(self) -> SpinTouchData:
        """Fetch data - called by coordinator on demand."""
        return self._data

    async def async_connect(self) -> bool:
        """Connect to the SpinTouch device."""
        # Don't connect if we're in the "stay disconnected" period
        if self._stay_disconnected:
            _LOGGER.debug(
                "Skipping connection - in reconnect delay period (allowing phone app access)"
            )
            return False

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
                    _LOGGER.warning("Device %s not found via Bluetooth proxy", self.address)
                    return False

                self._expected_disconnect = False
                self._reading_received = False
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
                self._data.connection_enabled = True
                _LOGGER.info("Connected to SpinTouch at %s - waiting for test data", self.address)
                self.async_set_updated_data(self._data)
                return True

            except BleakError as err:
                _LOGGER.error("Failed to connect to %s: %s", self.address, err)
                self._data.connected = False
                self.async_set_updated_data(self._data)
                return False
            except Exception as err:
                _LOGGER.exception("Unexpected error connecting to %s: %s", self.address, err)
                self._data.connected = False
                self.async_set_updated_data(self._data)
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
        self.async_set_updated_data(self._data)

    async def async_force_reconnect(self) -> None:
        """Force reconnection - cancels reconnect delay and connects immediately."""
        _LOGGER.info("Force reconnect requested")
        self._cancel_reconnect_timer()
        self._stay_disconnected = False
        self._reading_received = False
        self._data.connection_enabled = True
        self.async_set_updated_data(self._data)
        await self.async_connect()

    @callback  # type: ignore[misc]
    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle disconnection."""
        _LOGGER.info(
            "Disconnected from SpinTouch at %s (expected: %s)",
            self.address,
            self._expected_disconnect,
        )
        self._client = None
        self._data.connected = False
        self.async_set_updated_data(self._data)

        # If unexpected disconnect and not in stay_disconnected period, try to reconnect
        if not self._expected_disconnect and not self._stay_disconnected:
            _LOGGER.info("Unexpected disconnect - will reconnect on next advertisement")

    def _on_status_notification(self, _sender: int, _data: bytearray) -> None:
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
                self._reading_received = True
                self.async_set_updated_data(self._data)
                self._schedule_disconnect()

        except BleakError as err:
            _LOGGER.error("Failed to read data: %s", err)

    def _schedule_disconnect(self) -> None:
        """Schedule disconnect after delay to allow phone app access.

        This mirrors the ESPHome script behavior:
        1. Wait DISCONNECT_DELAY seconds
        2. If reading_received is still True (no new readings reset it), disconnect
        3. Stay disconnected for RECONNECT_DELAY seconds
        4. Then re-enable connections
        """
        # Cancel any existing timer and restart (mode: restart behavior)
        self._cancel_disconnect_timer()

        # Mark that we received a reading - will be checked when timer fires
        self._reading_received = True

        @callback  # type: ignore[misc]
        def _disconnect_callback() -> None:
            # Only disconnect if we still have reading_received=True
            # (if new data came in, the timer was restarted)
            if self._reading_received:
                _LOGGER.info(
                    "No new data after %ds, disconnecting to allow phone app access",
                    DISCONNECT_DELAY,
                )
                self._stay_disconnected = True
                self._data.connection_enabled = False
                self.async_set_updated_data(self._data)
                self.hass.async_create_task(self._async_disconnect_and_schedule_reconnect())

        self._disconnect_timer = self.hass.loop.call_later(DISCONNECT_DELAY, _disconnect_callback)
        _LOGGER.debug("Disconnect timer scheduled for %ds", DISCONNECT_DELAY)

    async def _async_disconnect_and_schedule_reconnect(self) -> None:
        """Disconnect and schedule reconnection after delay."""
        await self.async_disconnect()
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection after RECONNECT_DELAY."""
        self._cancel_reconnect_timer()

        @callback  # type: ignore[misc]
        def _reconnect_callback() -> None:
            _LOGGER.info(
                "Reconnect delay (%ds) expired, re-enabling connection",
                RECONNECT_DELAY,
            )
            self._stay_disconnected = False
            self._reading_received = False
            self._data.connection_enabled = True
            self.async_set_updated_data(self._data)

            # Check if device is currently visible - if so, connect immediately
            # This handles the case where device advertised during stay_disconnected period
            # Check both connectable and non-connectable advertisements
            service_info = bluetooth.async_last_service_info(
                self.hass, self.address, connectable=True
            ) or bluetooth.async_last_service_info(self.hass, self.address, connectable=False)
            if service_info:
                _LOGGER.info(
                    "Device %s is currently visible, attempting connection",
                    self.address,
                )
                self.hass.async_create_task(self.async_connect())
            else:
                _LOGGER.debug(
                    "Device %s not currently visible, will connect when seen",
                    self.address,
                )

        self._reconnect_timer = self.hass.loop.call_later(RECONNECT_DELAY, _reconnect_callback)
        _LOGGER.info(
            "Reconnect scheduled in %ds (phone app can connect now)",
            RECONNECT_DELAY,
        )

    def _cancel_disconnect_timer(self) -> None:
        """Cancel the disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None

    def _cancel_reconnect_timer(self) -> None:
        """Cancel the reconnect timer."""
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
            self._reconnect_timer = None

    @callback  # type: ignore[misc]
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

        # Auto-connect when device is seen (if not in stay_disconnected period)
        if (
            not self._data.connected
            and not self._stay_disconnected
            and not self._connect_lock.locked()
        ):
            _LOGGER.debug("Device seen, attempting connection...")
            self.hass.async_create_task(self.async_connect())
        elif self._stay_disconnected:
            _LOGGER.debug("Device seen but in reconnect delay period - not connecting")
