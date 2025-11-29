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

from .const import (
    ACK_CHARACTERISTIC_UUID,
    DATA_CHARACTERISTIC_UUID,
    DISCONNECT_DELAY,
    DISK_TYPE_MAP,
    DOMAIN,
    END_SIGNATURE,
    END_SIGNATURE_OFFSET,
    ENTRY_SIZE,
    HEADER_SIZE,
    MAX_ENTRIES,
    METADATA_OFFSET,
    MIN_DATA_SIZE,
    PARAM_ID_TO_SENSOR,
    RECONNECT_DELAY,
    SANITIZER_TYPE_MAP,
    START_SIGNATURE,
    STATUS_CHARACTERISTIC_UUID,
    TIMESTAMP_OFFSET,
    TIMESTAMP_SIZE,
)
from .util import TimerManager

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)

# Timer names for the coordinator
TIMER_DISCONNECT = "disconnect"
TIMER_RECONNECT = "reconnect"


class SpinTouchData:
    """Container for SpinTouch sensor data."""

    def __init__(self) -> None:
        """Initialize data container."""
        self.values: dict[str, float | None] = {}
        self.last_reading_time: datetime | None = None
        self.report_time: datetime | None = None
        self.connected: bool = False
        self.connection_enabled: bool = True
        self.detected_param_ids: set[int] = set()

        # Metadata from BLE data
        self.num_valid_results: int = 0
        self.disk_type_index: int | None = None
        self.sanitizer_type_index: int | None = None
        self.disk_type: str | None = None
        self.sanitizer_type: str | None = None

    @property
    def detected_disk_series(self) -> str | None:
        """Auto-detect disk series based on which param_ids are present."""
        if not self.detected_param_ids:
            return None

        has_chlorine = 0x01 in self.detected_param_ids or 0x02 in self.detected_param_ids
        has_bromine = 0x03 in self.detected_param_ids
        has_borate_0e = 0x0E in self.detected_param_ids

        if has_bromine:
            return "203"
        if has_chlorine and not has_borate_0e:
            return "303"
        if has_borate_0e and not has_chlorine and not has_bromine:
            return "204"
        if has_chlorine:
            return "303"

        return None

    def update_from_bytes(self, data: bytes) -> bool:
        """Parse BLE data and update values.

        Returns True if data was valid AND represents a new report.
        """
        if len(data) < MIN_DATA_SIZE:
            _LOGGER.warning("Data too short: %d bytes (expected %d)", len(data), MIN_DATA_SIZE)
            return False

        _LOGGER.debug("Parsing %d bytes of SpinTouch data", len(data))

        if not self._validate_signatures(data):
            return False

        self._parse_metadata(data)

        old_report_time = self.report_time
        self._parse_report_timestamp(data)

        if old_report_time is not None and self.report_time == old_report_time:
            _LOGGER.debug("Report timestamp unchanged, skipping update")
            return False

        entries_parsed = self._parse_entries(data)
        _LOGGER.debug("Parsed %d parameter entries", entries_parsed)

        self._log_disk_info()
        self._calculate_derived_values()

        self.last_reading_time = dt_util.utcnow()
        return True

    def _validate_signatures(self, data: bytes) -> bool:
        """Validate start and end signatures."""
        if data[:HEADER_SIZE] != START_SIGNATURE:
            _LOGGER.warning(
                "Invalid start signature: %s (expected %s)",
                data[:HEADER_SIZE].hex(),
                START_SIGNATURE.hex(),
            )
            return False

        if len(data) >= END_SIGNATURE_OFFSET + 4:
            end_sig = data[END_SIGNATURE_OFFSET : END_SIGNATURE_OFFSET + 4]
            if end_sig != END_SIGNATURE:
                _LOGGER.warning(
                    "Invalid end signature: %s (expected %s)",
                    end_sig.hex(),
                    END_SIGNATURE.hex(),
                )
                # Continue anyway - signature check is informational

        return True

    def _parse_entries(self, data: bytes) -> int:
        """Parse parameter entries from BLE data."""
        offset = HEADER_SIZE
        entries_parsed = 0

        while offset + ENTRY_SIZE <= len(data) and entries_parsed < MAX_ENTRIES:
            test_type = data[offset]
            decimals = data[offset + 1]

            if test_type == 0 and decimals == 0:
                break

            self._parse_single_entry(data, offset, test_type, decimals)
            offset += ENTRY_SIZE
            entries_parsed += 1

        return entries_parsed

    def _parse_single_entry(self, data: bytes, offset: int, test_type: int, decimals: int) -> None:
        """Parse a single test result entry."""
        self.detected_param_ids.add(test_type)

        sensor = PARAM_ID_TO_SENSOR.get(test_type)
        if not sensor:
            _LOGGER.debug(
                "Unknown TestType 0x%02X at offset %d (decimals=%d)",
                test_type,
                offset,
                decimals,
            )
            return

        try:
            value = struct.unpack_from("<f", data, offset + 2)[0]
            if self._is_valid_value(value, sensor):
                display_decimals = decimals if decimals < 10 else sensor.decimals
                self.values[sensor.key] = round(value, display_decimals)
                _LOGGER.debug(
                    "TestType 0x%02X -> %s: %.2f %s",
                    test_type,
                    sensor.name,
                    value,
                    sensor.unit or "",
                )
            else:
                _LOGGER.debug(
                    "TestType 0x%02X -> %s: invalid value %s",
                    test_type,
                    sensor.name,
                    value,
                )
        except struct.error as err:
            _LOGGER.error("Failed to parse TestType 0x%02X: %s", test_type, err)

    def _is_valid_value(self, value: float, sensor: object) -> bool:
        """Check if a sensor value is valid."""
        return (
            value is not None
            and not math.isnan(value)
            and sensor.min_valid <= value <= sensor.max_valid  # type: ignore[attr-defined]
        )

    def _log_disk_info(self) -> None:
        """Log disk type information."""
        if self.disk_type:
            _LOGGER.info(
                "Disk type: %s, Sanitizer: %s, Valid results: %d",
                self.disk_type,
                self.sanitizer_type or "Unknown",
                self.num_valid_results,
            )
        elif self.detected_disk_series:
            _LOGGER.info("Auto-detected disk series: %s", self.detected_disk_series)

    def _calculate_derived_values(self) -> None:
        """Calculate derived sensor values."""
        fc = self.values.get("free_chlorine")
        tc = self.values.get("total_chlorine")
        cya = self.values.get("cyanuric_acid")

        if fc is not None and tc is not None:
            cc = tc - fc
            self.values["combined_chlorine"] = round(max(0, cc), 2)

        if fc is not None and cya is not None and cya > 0:
            self.values["fc_cya_ratio"] = round((fc / cya) * 100, 1)

    def _parse_metadata(self, data: bytes) -> None:
        """Parse metadata from BLE data (bytes 84-86)."""
        if len(data) < METADATA_OFFSET + 3:
            return

        self.num_valid_results = data[METADATA_OFFSET]
        self.disk_type_index = data[METADATA_OFFSET + 1]
        self.sanitizer_type_index = data[METADATA_OFFSET + 2]

        self.disk_type = DISK_TYPE_MAP.get(
            self.disk_type_index, f"Unknown ({self.disk_type_index})"
        )
        self.sanitizer_type = SANITIZER_TYPE_MAP.get(
            self.sanitizer_type_index, f"Unknown ({self.sanitizer_type_index})"
        )

        _LOGGER.debug(
            "Metadata: valid=%d, disk_idx=%d (%s), sanitizer_idx=%d (%s)",
            self.num_valid_results,
            self.disk_type_index,
            self.disk_type,
            self.sanitizer_type_index,
            self.sanitizer_type,
        )

    def _parse_report_timestamp(self, data: bytes) -> None:
        """Parse the report timestamp from BLE data."""
        if len(data) < TIMESTAMP_OFFSET + TIMESTAMP_SIZE:
            _LOGGER.warning("Data too short for timestamp parsing")
            return

        try:
            year = 2000 + data[TIMESTAMP_OFFSET]
            month = data[TIMESTAMP_OFFSET + 1]
            day = data[TIMESTAMP_OFFSET + 2]
            hour = data[TIMESTAMP_OFFSET + 3]
            minute = data[TIMESTAMP_OFFSET + 4]
            second = data[TIMESTAMP_OFFSET + 5]
            ampm = data[TIMESTAMP_OFFSET + 6]
            military = data[TIMESTAMP_OFFSET + 7]

            # Convert 12h to 24h if not military time
            if military == 0:
                if ampm == 1 and hour < 12:
                    hour += 12
                elif ampm == 0 and hour == 12:
                    hour = 0

            if not self._is_valid_timestamp(year, month, day, hour, minute, second):
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

            local_tz = dt_util.get_default_time_zone()
            naive_dt = dt_module.datetime(year, month, day, hour, minute, second)
            self.report_time = naive_dt.replace(tzinfo=local_tz)

            _LOGGER.debug(
                "Report timestamp: %s (military=%d, ampm=%d)",
                self.report_time.isoformat(),
                military,
                ampm,
            )
        except (ValueError, IndexError) as err:
            _LOGGER.warning("Failed to parse report timestamp: %s", err)

    @staticmethod
    def _is_valid_timestamp(
        year: int, month: int, day: int, hour: int, minute: int, second: int
    ) -> bool:
        """Validate timestamp component ranges."""
        return (
            2020 <= year <= 2099
            and 1 <= month <= 12
            and 1 <= day <= 31
            and 0 <= hour <= 23
            and 0 <= minute <= 59
            and 0 <= second <= 59
        )


class SpinTouchCoordinator(DataUpdateCoordinator[SpinTouchData]):  # type: ignore[misc]
    """Coordinator for SpinTouch BLE device.

    Connection lifecycle:
    1. Auto-connect when device is discovered via Bluetooth advertisement
    2. Stay connected and listen for status notifications
    3. When data is received, start disconnect timer
    4. After DISCONNECT_DELAY (10s) with no new data, disconnect
    5. Stay disconnected for RECONNECT_DELAY (5 min) to allow phone app
    6. After reconnect delay, enable connection again
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
            update_interval=None,
        )
        self.address = address
        self._service_info = service_info
        self._client: BleakClient | None = None
        self._data = SpinTouchData()

        # Timer manager for disconnect/reconnect scheduling
        self._timers = TimerManager(hass, _LOGGER)

        # Connection state flags
        self._expected_disconnect = False
        self._stay_disconnected = False
        self._reading_received = False
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
        self._timers.cancel(TIMER_DISCONNECT)
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
        self._timers.cancel(TIMER_RECONNECT)
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

        if not self._expected_disconnect and not self._stay_disconnected:
            _LOGGER.info("Unexpected disconnect - will reconnect on next advertisement")

    def _on_status_notification(self, _sender: int, _data: bytearray) -> None:
        """Handle status notification from SpinTouch."""
        _LOGGER.debug("Status notification received, reading data...")
        self.hass.async_create_task(self._async_read_data())

    async def _async_read_data(self) -> None:
        """Read data from the SpinTouch device."""
        if not self._client or not self._client.is_connected:
            _LOGGER.warning("Cannot read data - not connected")
            return

        try:
            data = await self._client.read_gatt_char(DATA_CHARACTERISTIC_UUID)
            _LOGGER.info("Received %d bytes from SpinTouch", len(data))

            if self._data.update_from_bytes(bytes(data)):
                _LOGGER.info(
                    "SpinTouch NEW reading: FC=%.2f pH=%.2f Alk=%.0f Ca=%.0f CYA=%.0f Salt=%.0f",
                    self._data.values.get("free_chlorine", 0),
                    self._data.values.get("ph", 0),
                    self._data.values.get("alkalinity", 0),
                    self._data.values.get("calcium", 0),
                    self._data.values.get("cyanuric_acid", 0),
                    self._data.values.get("salt", 0),
                )

                await self._async_send_ack()

                self._reading_received = True
                self.async_set_updated_data(self._data)
                self._schedule_disconnect()
            else:
                _LOGGER.info("SpinTouch data unchanged (same report timestamp), skipping update")

        except BleakError as err:
            _LOGGER.error("Failed to read data: %s", err)

    async def _async_send_ack(self) -> None:
        """Send acknowledgment to SpinTouch device."""
        if not self._client or not self._client.is_connected:
            return

        try:
            await self._client.write_gatt_char(ACK_CHARACTERISTIC_UUID, bytes([0x01]))
            _LOGGER.debug("Sent ACK to SpinTouch")
        except BleakError as err:
            _LOGGER.warning("Failed to send ACK: %s", err)

    def _schedule_disconnect(self) -> None:
        """Schedule disconnect after delay to allow phone app access."""
        self._reading_received = True

        def _disconnect_callback() -> None:
            if self._reading_received:
                _LOGGER.info(
                    "No new data after %ds, disconnecting to allow phone app access",
                    DISCONNECT_DELAY,
                )
                self._stay_disconnected = True
                self._data.connection_enabled = False
                self.async_set_updated_data(self._data)
                self.hass.async_create_task(self._async_disconnect_and_schedule_reconnect())

        self._timers.schedule(TIMER_DISCONNECT, DISCONNECT_DELAY, _disconnect_callback)

    async def _async_disconnect_and_schedule_reconnect(self) -> None:
        """Disconnect and schedule reconnection after delay."""
        await self.async_disconnect()
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection after RECONNECT_DELAY."""

        def _reconnect_callback() -> None:
            _LOGGER.info(
                "Reconnect delay (%ds) expired, re-enabling connection",
                RECONNECT_DELAY,
            )
            self._stay_disconnected = False
            self._reading_received = False
            self._data.connection_enabled = True
            self.async_set_updated_data(self._data)

            _LOGGER.info("Attempting to reconnect to %s", self.address)
            self.hass.async_create_task(self.async_connect())

        self._timers.schedule(TIMER_RECONNECT, RECONNECT_DELAY, _reconnect_callback)
        _LOGGER.info(
            "Reconnect scheduled in %ds (phone app can connect now)",
            RECONNECT_DELAY,
        )

    @callback  # type: ignore[misc]
    def async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle Bluetooth event - device advertisement received."""
        _LOGGER.info(
            "Bluetooth advertisement from %s: %s (RSSI: %s, connected: %s, stay_disconnected: %s)",
            self.address,
            change,
            service_info.rssi,
            self._data.connected,
            self._stay_disconnected,
        )
        self._service_info = service_info

        if (
            not self._data.connected
            and not self._stay_disconnected
            and not self._connect_lock.locked()
        ):
            _LOGGER.info("Device seen and not connected, attempting connection...")
            self.hass.async_create_task(self.async_connect())
        elif self._stay_disconnected:
            _LOGGER.info("Device seen but in reconnect delay period - not connecting")
