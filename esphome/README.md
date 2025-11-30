# ESPHome Direct Configuration for SpinTouch

This directory contains an ESPHome configuration for directly connecting to a LaMotte SpinTouch device using a dedicated ESP32.

## When to Use This Approach

This ESPHome configuration is an **alternative** to using the custom Home Assistant integration with Bluetooth Proxies. Choose this approach when:

- You don't have existing ESPHome Bluetooth Proxies
- You want a dedicated ESP32 device for SpinTouch
- You need local processing without Home Assistant dependency
- You want the device to work standalone with its own web UI
- You need direct BLE connection without proxy overhead

## Recommended Approach

For most users, we recommend using the **custom Home Assistant integration** (`custom_components/spintouch/`) with [ESPHome Bluetooth Proxies](https://esphome.io/components/bluetooth_proxy/). This approach:

- Uses your existing infrastructure (no new hardware needed)
- Provides automatic device discovery
- Has full Home Assistant integration with reconfiguration support
- Supports multiple SpinTouch devices easily

### Setting Up a Bluetooth Proxy

If you don't have a Bluetooth Proxy yet, you can set one up using any ESP32 device:

1. Create a new ESPHome device with Bluetooth Proxy enabled:
   ```yaml
   esp32_ble_tracker:
     scan_parameters:
       active: true

   bluetooth_proxy:
     active: true
   ```

2. Flash the device and add it to Home Assistant

3. Install the SpinTouch custom integration from this repository

See the [ESPHome Bluetooth Proxy documentation](https://esphome.io/components/bluetooth_proxy/) for complete setup instructions.

## Hardware Requirements

For this ESPHome direct approach:

- ESP32 board (ESP32-C3, ESP32-S3, or classic ESP32)
- The example uses `lolin_c3_mini` but can be adapted for other boards

## Setup

1. Copy `spintouch.yaml` to your ESPHome configuration directory

2. Create a `secrets.yaml` file with:
   ```yaml
   wifi_ssid: "your_wifi_ssid"
   wifi_password: "your_wifi_password"
   ```

3. Update the `spintouch_mac` substitution with your SpinTouch's Bluetooth MAC address:
   ```yaml
   substitutions:
     spintouch_mac: "XX:XX:XX:XX:XX:XX"
   ```

   To find your MAC address, power on your SpinTouch and check the ESPHome logs - it will auto-detect SpinTouch devices by their service UUID.

4. Customize the ideal ranges for your pool:
   ```yaml
   substitutions:
     fc_min: "1.0"
     fc_max: "3.0"
     ph_min: "7.2"
     ph_max: "7.6"
     # ... etc
   ```

5. Compile and upload:
   ```bash
   esphome run spintouch.yaml
   ```

## Features

### Sensors

All water quality parameters are supported:

| Sensor | Unit | Description |
|--------|------|-------------|
| Free Chlorine | ppm | Active sanitizer level |
| Total Chlorine | ppm | Total chlorine (free + combined) |
| Combined Chlorine | ppm | Calculated (total - free) |
| Bromine | ppm | For bromine-sanitized pools |
| pH | - | Acidity/alkalinity |
| Total Alkalinity | ppm | Buffer capacity |
| Calcium Hardness | ppm | Water hardness |
| Cyanuric Acid | ppm | Stabilizer level |
| Salt | ppm | For saltwater pools |
| Copper | ppm | Metal content |
| Iron | ppm | Metal content |
| Phosphate | ppb | Algae nutrient |
| Borate | ppm | Water softener additive |
| FC/CYA Ratio | % | Chlorine effectiveness |

### Range Indicators

Binary sensors indicate whether each parameter is within configured ideal ranges.

### Connection Management

The device automatically:
- Connects when SpinTouch is powered on
- Reads test results when available
- Disconnects after reading to allow phone app access
- Reconnects after a configurable delay

### Web UI

Access the built-in web server at the device's IP address to:
- View all sensor values
- Adjust disconnect/reconnect timing
- View connection status

## Comparison with Custom Integration

| Feature | ESPHome Direct | Custom Integration |
|---------|---------------|-------------------|
| Hardware | Dedicated ESP32 | Uses existing proxies |
| Setup | Manual YAML | Config flow UI |
| Discovery | Manual MAC entry | Automatic |
| Standalone | Yes (web UI) | No (needs HA) |
| Multi-device | One ESP32 per device | Multiple via proxies |
| Updates | ESPHome OTA | HACS |

## Troubleshooting

### Device not connecting

1. Verify the MAC address is correct
2. Ensure SpinTouch is powered on and in range
3. Check that no other device (phone app) is connected

### No data received

1. Run a test on the SpinTouch device
2. Check logs for "Status notification received"
3. Verify the device is close enough to ESP32

### Values show NaN

Parameters only populate after a test is run on the SpinTouch. NaN means that parameter wasn't included in the test (depends on SpinDisk type).

## Protocol Details

See the main [RESEARCH.md](../RESEARCH.md) for full BLE protocol documentation derived from the decompiled Android app.
