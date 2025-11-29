# Architecture Documentation

This document describes the technical architecture of the SpinTouch Home Assistant integration.

## Overview

The SpinTouch integration connects to LaMotte WaterLink Spin Touch water testing devices via Bluetooth Low Energy (BLE). It leverages Home Assistant's Bluetooth component and ESPHome Bluetooth proxies for connectivity.

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  SpinTouch  │──BLE───▶│ Bluetooth Proxy  │──API───▶│  Home Assistant │
│   Device    │         │    (ESPHome)     │         │                 │
└─────────────┘         └──────────────────┘         │  ┌───────────┐  │
                                                     │  │ SpinTouch │  │
                                                     │  │Integration│  │
                                                     │  └───────────┘  │
                                                     └─────────────────┘
```

## File Structure

```
custom_components/spintouch/
├── __init__.py          # Integration setup and Bluetooth callbacks
├── config_flow.py       # UI configuration flow
├── coordinator.py       # BLE connection and data management
├── sensor.py            # Water quality sensor entities
├── binary_sensor.py     # Connection status sensors
├── button.py            # Force reconnect button
├── base.py              # Shared entity mixin
├── util.py              # Timer management utilities
├── const.py             # Constants and sensor definitions
├── manifest.json        # Integration metadata
├── strings.json         # UI strings (base)
└── translations/
    └── en.json          # English translations
```

## Component Responsibilities

### `__init__.py`

- Registers the integration with Home Assistant
- Sets up Bluetooth advertisement callbacks
- Creates the coordinator instance
- Forwards setup to entity platforms

**Key Functions:**
- `async_setup_entry()`: Initialize integration from config entry
- `async_unload_entry()`: Clean up on removal

### `coordinator.py`

The heart of the integration. Manages BLE connection lifecycle and data parsing.

**Classes:**

`SpinTouchData`
- Container for parsed sensor values
- Handles BLE data parsing via `update_from_bytes()`
- Validates signatures and extracts parameters
- Calculates derived values (Combined Chlorine, FC/CYA Ratio)

`SpinTouchCoordinator`
- Extends `DataUpdateCoordinator`
- Manages BLE connection state machine
- Handles disconnect/reconnect timing
- Processes status notifications

**Connection State Machine:**

```
                    ┌──────────────────┐
                    │   Disconnected   │
                    └────────┬─────────┘
                             │
           Device seen (BLE advertisement)
                             │
                             ▼
                    ┌──────────────────┐
                    │   Connecting     │
                    └────────┬─────────┘
                             │
                     Success │ Failure
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌──────────────────┐         ┌──────────────────┐
     │    Connected     │         │ Visibility Check │◀──┐
     └────────┬─────────┘         └────────┬─────────┘   │
              │                            │             │
    Data received                   Device visible?     No
              │                            │             │
              ▼                           Yes            │
     ┌──────────────────┐                  │             │
     │ Wait 10 seconds  │                  ▼             │
     └────────┬─────────┘         ┌──────────────────┐   │
              │                   │   Connecting     │───┘
              ▼                   └──────────────────┘
     ┌──────────────────┐
     │   Disconnect     │
     └────────┬─────────┘
              │
              ▼
     ┌──────────────────┐
     │ Wait 5 minutes   │ (allows phone app access)
     └────────┬─────────┘
              │
              ▼
     ┌──────────────────┐
     │   Reconnect      │
     └──────────────────┘
```

### `sensor.py`

Creates sensor entities for water quality parameters.

**Classes:**

`SpinTouchSensor`
- Generic sensor for measured parameters
- Uses `RestoreEntity` for state persistence
- Maps to sensor definitions in `const.py`

`SpinTouchLastReadingSensor`
- Timestamp of last successful data read

`SpinTouchReportTimeSensor`
- Timestamp from the SpinTouch device itself

`SpinTouchWaterQualitySensor`
- Overall water quality status
- Compares values against ideal ranges
- Returns "OK" or list of issues

### `binary_sensor.py`

**Classes:**

`SpinTouchConnectedSensor`
- Shows current BLE connection status

`SpinTouchConnectionEnabledSensor`
- Shows if connection is enabled (not in cooldown)

### `button.py`

**Classes:**

`SpinTouchForceReconnectButton`
- Triggers immediate reconnection attempt
- Bypasses reconnect delay period

### `base.py`

**Classes:**

`SpinTouchEntity`
- Mixin providing shared device info
- Eliminates code duplication across entities

### `util.py`

**Classes:**

`TimerManager`
- Manages scheduled callbacks (disconnect, reconnect, visibility)
- Provides clean interface for timer operations

**Functions:**

`restore_float_state()` / `restore_datetime_state()`
- Helper functions for RestoreEntity pattern

### `const.py`

Contains all constants and sensor definitions:

- BLE UUIDs
- Timing constants
- Data parsing offsets
- Sensor definitions with param_id mappings
- Disk and sanitizer type mappings

## BLE Protocol

### GATT Profile

| Characteristic | UUID | Purpose |
|----------------|------|---------|
| Test Data | `...10` | Read test results (91 bytes) |
| Status | `...11` | Notifications when data ready |
| Send Test | `...12` | Send test command (unused) |
| Acknowledgment | `...13` | Send ACK after reading |

### Data Format (91 bytes)

```
Offset  Size  Description
------  ----  -----------
0-3     4     Start signature [0x01, 0x02, 0x03, 0x05]
4-75    72    12 test entries × 6 bytes each
76-83   8     Timestamp (YY MM DD HH MM SS AM/PM MIL)
84      1     Number of valid results
85      1     Disk type index
86      1     Sanitizer type index
87-90   4     End signature [0x07, 0x0B, 0x0D, 0x11]
```

### Test Entry Format (6 bytes)

```
Byte 0:    Param ID (identifies the chemical)
Byte 1:    Decimal places for display
Bytes 2-5: Float32 value (little-endian)
```

## Data Flow

1. **Discovery**: Home Assistant detects SpinTouch via BLE service UUID
2. **Connection**: Integration connects through Bluetooth proxy
3. **Subscription**: Subscribe to status notifications
4. **Notification**: Device notifies when test data is ready
5. **Read**: Integration reads the data characteristic
6. **Parse**: `SpinTouchData.update_from_bytes()` extracts values
7. **Update**: Coordinator notifies entities of new data
8. **Acknowledge**: Send ACK to device
9. **Disconnect**: After delay, disconnect to allow phone app
10. **Reconnect**: After cooldown, listen for device again

## Error Handling

### Connection Failures

- Retry with exponential backoff via `bleak_retry_connector`
- Start visibility polling after unexpected disconnect
- Log errors at appropriate levels

### Data Validation

- Verify start/end signatures
- Validate timestamp ranges
- Check value ranges per sensor definition
- Skip duplicate reports (same timestamp)

### State Restoration

- `RestoreEntity` pattern preserves values across restarts
- Coordinator data initialized before entities load
- Graceful handling of missing historical data

## Configuration

### Config Entry Data

```python
{
    "address": "XX:XX:XX:XX:XX:XX",  # BLE MAC address
    "disk_series": "auto"            # Disk series selection
}
```

### Supported Disk Series

| Series | Description |
|--------|-------------|
| auto | Auto-detect from data |
| 203 | Chlorine/Bromine + Phosphate |
| 204 | High Range + Phosphate |
| 303 | Chlorine/Bromine + Borate |
| 304 | High Range + Borate |

## Testing

### Manual Testing

1. Run a test on the SpinTouch device
2. Check that sensors update with new values
3. Verify automatic disconnect after 10 seconds
4. Confirm reconnect after 5 minutes
5. Test force reconnect button
6. Verify state restoration after HA restart

### Debug Logging

```yaml
logger:
  logs:
    custom_components.spintouch: debug
    bleak: debug
```

## Dependencies

- `homeassistant>=2024.1.0`
- `bleak>=0.21.0` - BLE client library
- `bleak-retry-connector>=3.1.0` - Connection retry logic

## Future Considerations

1. **Options Flow**: Allow reconfiguration without re-adding
2. **Diagnostics**: Provide diagnostic download for troubleshooting
3. **Unit Tests**: Comprehensive test coverage
4. **Multiple Devices**: Support multiple SpinTouch devices
5. **Historical Data**: Optional cloud sync with LaMotte service
