<p align="center">
  <img src="brand/logo.png" alt="SpinTouch Logo" width="400">
</p>

<h1 align="center">LaMotte WaterLink Spin Touch Integration</h1>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/joyfulhouse/lamotte-spintouch/releases"><img src="https://img.shields.io/github/v/release/joyfulhouse/lamotte-spintouch" alt="GitHub Release"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  Home Assistant integration for the <strong>LaMotte WaterLink Spin Touch</strong> water testing device.<br>
  The Spin Touch is a handheld photometer that reads pool and spa water quality parameters via Bluetooth LE.
</p>

---

## Features

- **Auto-discovery** via Bluetooth service UUID
- **Works with ESPHome Bluetooth Proxies** - no dedicated hardware needed
- **Push-based updates** - device notifies on new readings (no polling)
- **Auto-disconnect** - allows phone app access after reading
- **State persistence** - sensor values survive Home Assistant restarts
- **Calculated metrics** - Combined Chlorine and FC/CYA Ratio

## Sensors

### Water Quality Parameters

| Parameter | Unit | Description |
|-----------|------|-------------|
| Free Chlorine | ppm | Active sanitizer level (0-15 ppm) |
| Total Chlorine | ppm | Free + Combined chlorine (0-15 ppm) |
| Bromine | ppm | For bromine-sanitized pools (0-33 ppm) |
| pH | - | Acidity/alkalinity (6.4-8.6) |
| Total Alkalinity | ppm | Buffering capacity (0-250 ppm) |
| Calcium Hardness | ppm | Water hardness (0-800/1200 ppm) |
| Cyanuric Acid | ppm | Chlorine stabilizer (5-150 ppm) |
| Salt | ppm | For saltwater pools (0-5000 ppm) |
| Copper | ppm | Metal content (0-3.0 ppm) |
| Iron | ppm | Metal content (0-3.0 ppm) |
| Phosphate | ppb | Algae nutrient (0-2000 ppb) |
| Borate | ppm | Water conditioner (0-80 ppm) |

### Calculated Sensors

| Sensor | Description |
|--------|-------------|
| Combined Chlorine | Total Chlorine - Free Chlorine |
| FC/CYA Ratio | Free Chlorine ÷ Cyanuric Acid × 100% |
| Water Quality | Overall status (OK or list of issues) |

### Diagnostic Sensors

| Sensor | Description |
|--------|-------------|
| Last Reading | Timestamp of last data update |
| Report Time | Timestamp from SpinTouch device |
| Connected | BLE connection status |
| Connection Enabled | Whether auto-connect is active |

### Controls

| Entity | Description |
|--------|-------------|
| Force Reconnect | Button to manually trigger reconnection |

## Requirements

- Home Assistant 2024.1.0 or newer
- [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy/) **or** built-in Bluetooth adapter
- LaMotte WaterLink Spin Touch device
- SpinDisk reagent cartridge (Series 203, 204, 303, 304, or 402)

### Setting Up a Bluetooth Proxy

If you don't have a Bluetooth Proxy yet, you can create one with any ESP32 device. Add this to your ESPHome configuration:

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

See the [ESPHome Bluetooth Proxy documentation](https://esphome.io/components/bluetooth_proxy/) for complete setup instructions.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/joyfulhouse/lamotte-spintouch` as **Integration**
4. Search for "LaMotte WaterLink Spin Touch" and install
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Extract and copy `custom_components/spintouch/` to your Home Assistant `custom_components/` directory
3. Restart Home Assistant

## Setup

> **Important:** The SpinTouch must be **powered on** and displaying a **test report** for Bluetooth discovery to work. The device only broadcasts when it has results to share.

1. Run a water test on your SpinTouch device
2. Keep the device on the results screen
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for "LaMotte WaterLink Spin Touch"
5. Select your device from the discovered list (or enter MAC address manually)
6. Choose your disk series (or leave as Auto-detect)

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| Bluetooth Address | MAC address of your SpinTouch device | Auto-discovered |
| Disk Series | SpinDisk series you use (203, 204, 303, 304, 402) | Auto-detect |

### Removal

To remove the integration:

1. Go to **Settings → Devices & Services**
2. Find "LaMotte WaterLink Spin Touch" in the integrations list
3. Click the three dots menu → **Delete**
4. Confirm the deletion

If you installed via HACS, you can also uninstall the integration through HACS after removing it from Home Assistant.

## How It Works

```
SpinTouch ─────BLE─────> ESPHome Proxy ─────> Home Assistant
                                               └── SpinTouch Integration
                                                   ├── Parses BLE data
                                                   ├── Creates sensors
                                                   └── Updates entities
```

### Connection Lifecycle

1. Device discovered via Bluetooth advertisement
2. Integration connects and subscribes to notifications
3. When test data is ready, device notifies integration
4. Integration reads data, parses it, updates sensors
5. After 10 seconds, integration disconnects (allowing phone app access)
6. After 5 minutes, integration listens for device again

This cycle ensures your phone app can still connect to view results and manage the device.

## SpinDisk Compatibility

| Series | Order Code | Tests | Notes |
|--------|------------|-------|-------|
| 203 | 4329-H/J | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Phosphate | Standard range |
| 303 | 4330-H/J | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Borate | Standard range |
| 204 | 4349-H/J | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Salt, Phosphate | High range Ca/Salt |
| 304 | 4350-H/J | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Salt, Borate | High range Ca/Salt |
| 402 | 4331-H/J | pH, Alk, Ca, Cu, Fe, Borate, Biguanide | Biguanide pools |

## Use Cases

### Pool Maintenance Automation

```yaml
automation:
  - alias: "Low Chlorine Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.spintouch_free_chlorine
        below: 1.0
    action:
      - service: notify.mobile_app
        data:
          title: "Pool Alert"
          message: "Free chlorine is low ({{ states('sensor.spintouch_free_chlorine') }} ppm). Consider adding chlorine."

  - alias: "pH Out of Range"
    trigger:
      - platform: numeric_state
        entity_id: sensor.spintouch_ph
        above: 7.8
      - platform: numeric_state
        entity_id: sensor.spintouch_ph
        below: 7.2
    action:
      - service: notify.mobile_app
        data:
          title: "Pool Alert"
          message: "pH is {{ states('sensor.spintouch_ph') }}. Target range: 7.2-7.6"
```

### Dashboard Card

```yaml
type: entities
title: Pool Water Quality
entities:
  - entity: sensor.spintouch_water_quality
  - entity: sensor.spintouch_free_chlorine
  - entity: sensor.spintouch_ph
  - entity: sensor.spintouch_alkalinity
  - entity: sensor.spintouch_calcium
  - entity: sensor.spintouch_cyanuric_acid
  - entity: sensor.spintouch_report_time
```

## Known Limitations

- **Single device support**: The integration connects to one SpinTouch device at a time
- **Device must be on results screen**: The SpinTouch only broadcasts via Bluetooth when displaying test results
- **Shared Bluetooth access**: The device can only connect to one client at a time - the integration automatically disconnects to allow phone app access
- **No remote test triggering**: Tests must be initiated manually on the physical device
- **Result persistence**: The integration reads the last test result stored on the device; historical data is not retained on the device

## Troubleshooting

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues and solutions.

### Quick Fixes

- **Device not discovered?** Make sure it's showing a test report screen
- **Connection fails?** Close the WaterLink app on your phone
- **Sensors show unknown?** Run a test to generate data
- **Phone app can't connect?** Wait for the 5-minute reconnect window

### Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.spintouch: debug
```

## Advanced: ESPHome Direct

For dedicated ESP32 integration without Home Assistant, see the [ESPHome directory](esphome/README.md).

Use ESPHome Direct when:
- No existing Bluetooth proxies
- Want local-only processing
- Need standalone operation with built-in web UI

For most users, the custom integration with [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy/) is the recommended approach.

## Advanced: LSI Calculation

The Langelier Saturation Index requires water temperature from an external sensor. See `homeassistant/lsi_template.yaml` for a template sensor example.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Technical design and data flow
- [Quality Scale](docs/QUALITY_SCALE.md) - Home Assistant compliance status
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Research](RESEARCH.md) - BLE protocol documentation

## Contributing

Contributions are welcome! This integration was developed through reverse engineering of the BLE protocol.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/joyfulhouse/lamotte-spintouch.git
cd lamotte-spintouch

# Install dependencies
uv sync --dev

# Run linting
uv run ruff check --fix custom_components/
uv run ruff format custom_components/

# Run type checking
uv run mypy custom_components/
```

## Disclaimer

This is an unofficial integration developed through reverse engineering. LaMotte and WaterLink are trademarks of LaMotte Company. This project is not affiliated with or endorsed by LaMotte.

## License

MIT License - see [LICENSE](LICENSE) for details.
