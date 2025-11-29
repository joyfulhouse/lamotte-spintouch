# LaMotte WaterLink Spin Touch Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for the **LaMotte WaterLink Spin Touch** water testing device. The Spin Touch is a handheld photometer that reads pool and spa water quality parameters via Bluetooth LE.

## Features

- **Auto-discovery** via Bluetooth service UUID
- **Works with ESPHome Bluetooth Proxies** - no dedicated hardware needed
- **Push-based updates** - device notifies on new readings
- **Auto-disconnect** - allows phone app access after reading
- **Comprehensive sensors** - all water quality parameters plus calculated metrics

## Sensors

| Parameter | Unit | Description |
|-----------|------|-------------|
| Free Chlorine | ppm | Active sanitizer level |
| Total Chlorine | ppm | Free + Combined chlorine |
| Combined Chlorine | ppm | Calculated (TC - FC) |
| pH | - | Acidity/alkalinity |
| Total Alkalinity | ppm | Buffering capacity |
| Calcium Hardness | ppm | Water hardness |
| Cyanuric Acid | ppm | Chlorine stabilizer |
| Salt | ppm | For saltwater pools |
| Iron | ppm | Metal content |
| Phosphate | ppb | Algae nutrient |
| FC/CYA Ratio | % | Sanitization effectiveness |

## Installation

> **Important:** The Spin Touch must be **powered on** and displaying a **report screen** (showing test results) for Bluetooth discovery to work. The device only advertises via BLE when it has results to share.

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "LaMotte WaterLink Spin Touch"
3. Install and restart Home Assistant
4. **Turn on your Spin Touch and navigate to a report screen**
5. Go to **Settings → Devices & Services → Add Integration**
6. Search for "LaMotte WaterLink Spin Touch"
7. Select your device (auto-discovered) or enter MAC address manually

### Manual Installation

1. Copy `custom_components/spintouch/` to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Add the integration via UI

## Requirements

- Home Assistant 2024.1.0 or newer
- ESPHome Bluetooth Proxy or built-in Bluetooth adapter
- LaMotte WaterLink Spin Touch device

## Alternative: ESPHome Direct

If you prefer a dedicated ESPHome device instead of using the custom integration:

See `esphome/spintouch.yaml` for a complete ESPHome configuration that connects directly to the Spin Touch.

**Use ESPHome Direct when:**
- No existing Bluetooth proxies available
- Want local processing without Home Assistant
- Need standalone operation

## How It Works

```
Spin Touch ──BLE──> Bluetooth Proxy ──ESPHome API──> Home Assistant
                    (existing)                        └── Custom Integration
                                                          └── Parses BLE data
                                                          └── Creates sensors
```

1. Spin Touch broadcasts BLE advertisements
2. Nearby Bluetooth proxy detects it by service UUID
3. Integration connects through proxy when device is seen
4. Subscribes to status notifications
5. Reads water quality data when test completes
6. Parses binary data and updates sensors
7. Disconnects after 10 seconds to allow phone app access

## BLE Protocol

The Spin Touch uses a custom GATT profile:

- **Service UUID**: `00000000-0000-1000-8000-bbbd00000000`
- **Data Characteristic**: `00000000-0000-1000-8000-bbbd00000010`
- **Status Notifications**: `00000000-0000-1000-8000-bbbd00000011`

Data format: 4-byte header + 6-byte entries [param_id, flags, float32_le]

## LSI Calculation

For Langelier Saturation Index calculation with your pool temperature sensor, see `homeassistant/lsi_template.yaml`.

## Contributing

Contributions are welcome! This integration was developed through reverse engineering of the BLE protocol.

## Disclaimer

This is an unofficial integration. LaMotte and WaterLink are trademarks of LaMotte Company. This project is not affiliated with or endorsed by LaMotte.

## License

MIT License
