# LaMotte WaterLink Spin Touch

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/joyfulhouse/lamotte-spintouch)](https://github.com/joyfulhouse/lamotte-spintouch/releases)
[![License](https://img.shields.io/github/license/joyfulhouse/lamotte-spintouch)](LICENSE)

Home Assistant integration for the **LaMotte WaterLink Spin Touch** water testing device. This integration connects directly to your SpinTouch via Bluetooth Low Energy (BLE) and exposes water quality readings as sensors.

## Features

- Direct Bluetooth connection (no cloud dependency)
- Real-time water quality readings
- Works offline
- Auto-discovery of SpinTouch devices

## Supported Parameters

| Sensor | Unit | Description |
|--------|------|-------------|
| Free Chlorine | ppm | Active sanitizer level |
| Total Chlorine | ppm | Combined chlorine measurement |
| pH | - | Water acidity/alkalinity |
| Total Alkalinity | ppm | pH buffer capacity |
| Calcium Hardness | ppm | Calcium concentration |
| Cyanuric Acid | ppm | UV stabilizer level |
| Salt | ppm | Salt concentration (for SWG pools) |
| Iron | ppm | Iron content |
| Phosphate | ppb | Phosphate level |

## Requirements

- Home Assistant 2025.11.0 or newer
- Bluetooth adapter or ESPHome Bluetooth Proxy
- LaMotte WaterLink Spin Touch device

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/joyfulhouse/lamotte-spintouch` as an **Integration**
4. Search for "LaMotte WaterLink Spin Touch" and install
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/joyfulhouse/lamotte-spintouch/releases)
2. Extract and copy `custom_components/spintouch` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Power on your SpinTouch device
2. Go to **Settings** → **Devices & Services**
3. Click **+ Add Integration**
4. Search for "LaMotte WaterLink Spin Touch"
5. Select your SpinTouch device from the list

The integration will automatically discover SpinTouch devices within Bluetooth range.

## Usage

After setup, sensors will appear under your SpinTouch device. Run a water test on your SpinTouch and the readings will sync automatically.

### ESPHome Bluetooth Proxy

For extended range, use an [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy.html). This allows the SpinTouch to be located further from your Home Assistant server.

Example ESPHome configuration is available in the `esphome/` directory of this repository.

## Troubleshooting

### Device not found
- Ensure the SpinTouch is powered on and in range
- Check that Bluetooth is enabled on your Home Assistant host
- If using ESPHome proxy, verify the proxy is connected

### No readings appear
- Run a water test on the SpinTouch
- Wait for the test to complete (30-60 seconds)
- Check the Home Assistant logs for connection errors

## Technical Details

This integration communicates with the SpinTouch using its BLE GATT profile:

- **Service UUID**: `00000000-0000-1000-8000-bbbd00000000`
- **Test Results**: `00000000-0000-1000-8000-bbbd00000010`
- **Status Notifications**: `00000000-0000-1000-8000-bbbd00000011`

## Contributing

Contributions are welcome! Please open an issue or pull request on [GitHub](https://github.com/joyfulhouse/lamotte-spintouch).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with or endorsed by LaMotte Company. Use at your own risk.
