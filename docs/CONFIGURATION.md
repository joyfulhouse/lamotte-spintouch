# Configuration

Full configuration reference for LaMotte SpinTouch.

## Adding the Integration

> The SpinTouch must be **powered on** and displaying a **test report screen** for
> Bluetooth discovery to work. The device only broadcasts when it has results to share.

1. Run a water test on your SpinTouch device and keep it on the results screen.
2. Go to **Settings → Devices & Services → Add Integration**.
3. Search for **LaMotte SpinTouch** and select it.
4. Select your device from the auto-discovered list, or enter the MAC address manually.
5. Choose your SpinDisk series (or leave as **Auto-detect**).

## Configuration Options

| Parameter | Description | Default |
|---|---|---|
| Bluetooth Address | MAC address of your SpinTouch device | Auto-discovered |
| Disk Series | SpinDisk series you use (203, 204, 303, 304, 402) | Auto-detect |

### Disk Series Selection

Choosing the correct disk series ensures that the integration maps chemical
parameters correctly. If you leave **Auto-detect**, the integration infers the
series from the device data on each test. Manual selection is useful when the
device returns ambiguous data.

| Series | Tests included |
|---|---|
| 203 | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Phosphate |
| 303 | FC, TC, Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Borate |
| 204 | FC, TC, Br, pH, Alk, Ca (HR), CYA, Cu, Salt, Phosphate |
| 304 | FC, TC, Br, pH, Alk, Ca (HR), CYA, Cu, Salt, Borate |
| 402 | pH, Alk, Ca, Cu, Fe, Borate, Biguanide |

## Reconfiguration

To change the disk series or Bluetooth address after initial setup, remove and
re-add the integration:

1. Go to **Settings → Devices & Services**.
2. Find **LaMotte SpinTouch** and click **⋮ → Delete**.
3. Re-add the integration with the updated settings.

An options flow for in-place reconfiguration is planned for a future release.

## Advanced Options

### Debug Logging

Add to `configuration.yaml` to enable verbose logging:

```yaml
logger:
  default: info
  logs:
    custom_components.spintouch: debug
```

### Connection Timing

The integration uses a fixed connection lifecycle to share BLE access with the
LaMotte phone app:

| Phase | Duration | Description |
|---|---|---|
| Post-read cooldown | 10 seconds | Wait before disconnecting after data received |
| Phone app window | 5 minutes | Disconnected; phone app can connect freely |
| Reconnect polling | 30 seconds | Interval to check for device advertisements |

These values are not configurable through the UI.
