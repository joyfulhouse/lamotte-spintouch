# Troubleshooting Guide

This guide helps resolve common issues with the LaMotte WaterLink Spin Touch integration.

## Device Not Discovered

### Symptom
The SpinTouch device doesn't appear in the Bluetooth discovery list.

### Solutions

1. **Power on the device and show results**

   The SpinTouch only broadcasts Bluetooth advertisements when it has test results to display. Make sure the device is:
   - Powered on
   - Showing a test report screen (not the main menu)

2. **Check Bluetooth proxy range**

   Ensure your ESPHome Bluetooth proxy or Home Assistant host is within range (~10 meters) of the SpinTouch.

3. **Verify proxy configuration**

   If using ESPHome Bluetooth proxies, ensure active scanning is enabled:
   ```yaml
   esp32_ble_tracker:
     scan_parameters:
       active: true
       interval: 100ms
       window: 50ms
   ```

4. **Restart Bluetooth**

   Try restarting your Bluetooth adapter or ESPHome proxy device.

---

## Device Not Connecting

### Symptom
Device is discovered but connection fails.

### Solutions

1. **Check for competing connections**

   The SpinTouch can only connect to one device at a time. Close the WaterLink app on your phone if it's running.

2. **Power cycle the SpinTouch**

   Turn the device off and on again, then run a new test to generate fresh results.

3. **Check Home Assistant logs**

   Look for connection errors:
   ```
   Settings → System → Logs
   Filter by "spintouch"
   ```

4. **Force reconnect**

   Use the "Force Reconnect" button entity in Home Assistant to manually trigger a connection attempt.

---

## Sensors Show "Unknown" or "Unavailable"

### Symptom
Sensor entities exist but show no values.

### Solutions

1. **Wait for first reading**

   After initial setup, sensors will show "Unknown" until the first test data is received. Run a test on the SpinTouch to generate data.

2. **Check connection status**

   Look at the "Connected" binary sensor. If it shows "Off", the device isn't connected.

3. **Verify disk compatibility**

   Different SpinDisk series provide different parameters. A disk 303 (Borate) won't have Phosphate readings, for example.

4. **Check the Connection Enabled sensor**

   After receiving data, the integration disconnects for 5 minutes to allow phone app access. During this time, "Connection Enabled" will be Off.

---

## Incorrect or Missing Parameters

### Symptom
Some expected water quality parameters are missing or seem wrong.

### Solutions

1. **Verify your disk series**

   | Disk Series | Parameters |
   |-------------|------------|
   | 203 | Br, pH, Alk, Ca, CYA, Cu, Fe, Salt, Phosphate |
   | 303 | FC, TC, pH, Alk, Ca, CYA, Cu, Fe, Salt, Borate |
   | 204 | FC, TC, pH, Alk, Ca (HR), CYA, Cu, Salt, Phosphate |
   | 304 | FC, TC, pH, Alk, Ca (HR), CYA, Cu, Salt, Borate |
   | 402 | pH, Alk, Ca, Cu, Fe, Borate, Biguanide |

2. **Bromine vs Chlorine**

   Bromine disks report Bromine instead of Free/Total Chlorine. This is expected behavior.

3. **Combined Chlorine calculation**

   Combined Chlorine is calculated as `Total Chlorine - Free Chlorine`. If either value is 0 or missing, Combined Chlorine may show 0.

---

## Device Disconnects Unexpectedly

### Symptom
The SpinTouch disconnects and doesn't reconnect.

### Solutions

1. **Check device battery/power**

   The SpinTouch may have powered off due to low battery or auto-sleep.

2. **Verify visibility checks are working**

   Check logs for:
   ```
   Device XX:XX:XX:XX:XX:XX now visible, attempting connection
   ```

3. **Wait for reconnect**

   After an unexpected disconnect, the integration polls every 30 seconds looking for the device. Power on the SpinTouch and show a report screen.

4. **Use Force Reconnect**

   The "Force Reconnect" button bypasses any waiting periods and attempts immediate connection.

---

## Integration Not Loading

### Symptom
The integration fails to load after installation.

### Solutions

1. **Check Home Assistant version**

   This integration requires Home Assistant 2024.1.0 or newer.

2. **Verify Bluetooth component**

   The integration depends on `bluetooth_adapters`. Ensure Bluetooth is enabled:
   ```
   Settings → System → Hardware → Configure Bluetooth
   ```

3. **Check for missing dependencies**

   The integration requires:
   - `bleak>=0.21.0`
   - `bleak-retry-connector>=3.1.0`

   These should be installed automatically, but can be verified in logs.

4. **Review error logs**

   Check for import errors or exceptions during startup:
   ```
   Settings → System → Logs → Show full logs
   ```

---

## Phone App Can't Connect

### Symptom
The LaMotte WaterLink app can't connect to the SpinTouch while Home Assistant is integrated.

### Solutions

1. **Wait for disconnect cycle**

   After receiving test data, the integration automatically disconnects for 5 minutes. Check the "Connection Enabled" binary sensor - when it's Off, the phone app can connect.

2. **Force disconnect**

   Reload the integration to force an immediate disconnect:
   ```
   Settings → Devices & Services → SpinTouch → ⋮ → Reload
   ```

3. **Understanding the connection cycle**

   ```
   Test received → Wait 10s → Disconnect → Wait 5 min → Reconnect
   ```

   During the 5-minute window, your phone app has exclusive access.

---

## Data Not Updating

### Symptom
Sensor values are stale and don't update after new tests.

### Solutions

1. **Verify connection**

   Check that the "Connected" sensor shows "On" when you run a test.

2. **Check report timestamp**

   The "Report Time" sensor shows when the last test was recorded on the device. If this isn't updating, the integration may not be receiving new data.

3. **Look for duplicate timestamps**

   The integration ignores data with the same timestamp to prevent duplicate updates. Check logs for:
   ```
   Report timestamp unchanged, skipping update
   ```

4. **Restart the integration**

   Reload the integration to reset the connection state.

---

## Getting Help

If you're still experiencing issues:

1. **Enable debug logging**

   Add to `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.spintouch: debug
   ```

2. **Collect logs**

   After reproducing the issue, download full logs from:
   ```
   Settings → System → Logs → Download full log
   ```

3. **Report an issue**

   Open an issue at: https://github.com/joyfulhouse/lamotte-spintouch/issues

   Include:
   - Home Assistant version
   - Integration version
   - SpinDisk series used
   - Relevant log excerpts
   - Steps to reproduce
