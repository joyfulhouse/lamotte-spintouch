# LaMotte SpinTouch

Home Assistant integration for the LaMotte WaterLink Spin Touch water testing device.

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![HACS][hacs-shield]][hacs]
[![CI][ci-shield]][ci]
[![Project Maintenance][maintenance-shield]][maintenance]
[![GitHub Sponsors][sponsors-shield]][sponsors]
[![Ko-fi][kofi-shield]][kofi]

## What It Does

The LaMotte SpinTouch integration connects Home Assistant to the LaMotte WaterLink Spin Touch,
a handheld photometer that reads pool and spa water quality parameters via Bluetooth LE. The
integration auto-discovers the device via Bluetooth, subscribes to push notifications when new
test results are ready, and creates sensor entities for every measured parameter. After receiving
data, it automatically disconnects to give the LaMotte phone app exclusive access for a 5-minute
window before reconnecting.

## Features

- Auto-discovery via Bluetooth service UUID and device name
- Works with ESPHome Bluetooth Proxies — no dedicated Bluetooth hardware required
- Push-based updates: device notifies when a new test is ready, no polling
- Auto-disconnect after reading to allow phone app access
- State persistence: sensor values survive Home Assistant restarts
- Calculated metrics: Combined Chlorine and FC/CYA Ratio
- Disk-series awareness: correctly maps parameters for Series 203, 204, 303, 304, and 402

## Prerequisites

- Home Assistant 2024.1.0 or newer
- LaMotte WaterLink Spin Touch device with SpinDisk reagent cartridge
- [ESPHome Bluetooth Proxy](https://esphome.io/components/bluetooth_proxy/) or a built-in Bluetooth adapter on the Home Assistant host

## Installation

See **[INSTALL.md](INSTALL.md)** for the complete guide.

**Quick version (HACS):** add this repository as a custom repository in HACS,
install **LaMotte SpinTouch**, restart Home Assistant, then add the integration
from **Settings → Devices & Services**.

[![Open in HACS][hacs-repo-shield]][hacs-repo]

## Configuration

> The SpinTouch must be **powered on** and displaying a **test report screen** for
> Bluetooth discovery to work. The device only broadcasts when it has results to share.

1. Run a water test on your SpinTouch device and keep it on the results screen.
2. Go to **Settings → Devices & Services → Add Integration** and search for
   **LaMotte SpinTouch**.
3. Select your device from the auto-discovered list, or enter the MAC address manually.
4. Choose your SpinDisk series (or leave as Auto-detect).

| Parameter | Description | Default |
|---|---|---|
| Bluetooth Address | MAC address of your SpinTouch | Auto-discovered |
| Disk Series | SpinDisk series (203, 204, 303, 304, 402) | Auto-detect |

To remove: **Settings → Devices & Services → LaMotte SpinTouch → ⋮ → Delete**.

## Supported Equipment

### Water Quality Sensors

| Parameter | Unit | Description |
|---|---|---|
| Free Chlorine | ppm | Active sanitizer level (0–15 ppm) |
| Total Chlorine | ppm | Free + Combined chlorine (0–15 ppm) |
| Bromine | ppm | For bromine-sanitized pools (0–33 ppm) |
| pH | — | Acidity/alkalinity (6.4–8.6) |
| Total Alkalinity | ppm | Buffering capacity (0–250 ppm) |
| Calcium Hardness | ppm | Water hardness (0–800/1200 ppm) |
| Cyanuric Acid | ppm | Chlorine stabilizer (5–150 ppm) |
| Salt | ppm | For saltwater pools (0–5000 ppm) |
| Copper | ppm | Metal content (0–3.0 ppm) |
| Iron | ppm | Metal content (0–3.0 ppm) |
| Phosphate | ppb | Algae nutrient (0–2000 ppb) |
| Borate | ppm | Water conditioner (0–80 ppm) |

### Calculated Sensors

| Sensor | Description |
|---|---|
| Combined Chlorine | Total Chlorine − Free Chlorine |
| FC/CYA Ratio | Free Chlorine ÷ Cyanuric Acid × 100 % |
| Water Quality | Overall status: "OK" or list of out-of-range parameters |

### Diagnostic Sensors and Controls

| Entity | Description |
|---|---|
| Last Reading | Timestamp of last data update |
| Report Time | Timestamp from the SpinTouch device |
| Connected | BLE connection status |
| Connection Enabled | Whether auto-connect is active |
| Force Reconnect | Button to manually trigger reconnection |

### SpinDisk Compatibility

| Series | Tests | Notes |
|---|---|---|
| 203 | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Phosphate | Standard range |
| 303 | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Borate | Standard range |
| 204 | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Salt, Phosphate | High-range Ca/Salt |
| 304 | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Salt, Borate | High-range Ca/Salt |
| 402 | pH, Alk, Ca, Cu, Fe, Borate, Biguanide | Biguanide pools |

## Automation Examples

### Low Chlorine Alert

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
```

### pH Out of Range

```yaml
automation:
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
          message: "pH is {{ states('sensor.spintouch_ph') }}. Target range: 7.2–7.6"
```

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for the full guide.

**Quick fixes:**

- **Device not discovered?** Make sure it is showing a test report screen.
- **Connection fails?** Close the WaterLink app on your phone.
- **Sensors show Unknown?** Run a test to generate data first.
- **Phone app can't connect?** Wait for the 5-minute reconnect window (check the Connection Enabled sensor).

**Debug logging:**

```yaml
logger:
  default: info
  logs:
    custom_components.spintouch: debug
```

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) to set up a development environment.

## Support

- Join the [JoyfulHouse Discord](https://discord.gg/gc4eTPwxjJ) for support and discussion across all JoyfulHouse Home Assistant integrations and libraries.
- **Issues:** <https://github.com/joyfulhouse/lamotte-spintouch/issues>
- **Discussions / questions:** open an issue with the `question` label.

## Support Development

If this project is useful to you, please consider supporting its development:

- [GitHub Sponsors][sponsors]
- [Ko-fi][kofi]

## License

This project is licensed under the **MIT** License — see [LICENSE](LICENSE) for details.

## Credits

Built and maintained by [JoyfulHouse](https://github.com/joyfulhouse).

> This is an unofficial integration developed through reverse engineering of the BLE protocol.
> LaMotte and WaterLink are trademarks of LaMotte Company. This project is not affiliated with
> or endorsed by LaMotte.

<!-- Badge links -->
[releases-shield]: https://img.shields.io/github/release/joyfulhouse/lamotte-spintouch.svg?style=for-the-badge
[releases]: https://github.com/joyfulhouse/lamotte-spintouch/releases
[license-shield]: https://img.shields.io/github/license/joyfulhouse/lamotte-spintouch.svg?style=for-the-badge
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacs-repo-shield]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-repo]: https://my.home-assistant.io/redirect/hacs_repository/?owner=joyfulhouse&repository=lamotte-spintouch&category=integration
[ci-shield]: https://img.shields.io/github/actions/workflow/status/joyfulhouse/lamotte-spintouch/validate.yaml?style=for-the-badge&label=CI
[ci]: https://github.com/joyfulhouse/lamotte-spintouch/actions
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40btli-blue.svg?style=for-the-badge
[maintenance]: https://github.com/btli
[sponsors-shield]: https://img.shields.io/badge/sponsor-GitHub-EA4AAA.svg?style=for-the-badge&logo=githubsponsors&logoColor=white
[sponsors]: https://github.com/sponsors/btli
[kofi-shield]: https://img.shields.io/badge/Ko--fi-donate-FF5E5B.svg?style=for-the-badge&logo=ko-fi&logoColor=white
[kofi]: https://ko-fi.com/bryanli
