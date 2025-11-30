# Pool Chemistry Automations

Sample Home Assistant automations for the LaMotte SpinTouch integration.

## Files

| File | Description |
|------|-------------|
| `sync_to_intellicenter.yaml` | Syncs SpinTouch readings to Pentair IntelliCenter |
| `chemistry_alerts.yaml` | Alerts when chemistry values are out of range |

## Installation

### Option 1: Include Directory

Add to your `configuration.yaml`:

```yaml
automation: !include_dir_merge_list automations/
```

Then copy the YAML files to your Home Assistant `automations/` directory.

### Option 2: Copy Individual Automations

Copy the automation blocks you want into your existing automations configuration.

### Option 3: UI Import

1. Open Home Assistant → Settings → Automations
2. Click the three-dot menu → Import automation
3. Paste the YAML content

## IntelliCenter Sync

The `sync_to_intellicenter.yaml` automation updates these IntelliChem values when a SpinTouch test completes:

| SpinTouch Sensor | IntelliCenter Entity |
|------------------|---------------------|
| `sensor.spintouch_alkalinity` | `number.intellichem_alkalinity` |
| `sensor.spintouch_calcium` | `number.intellichem_calcium_hardness` |
| `sensor.spintouch_cyanuric_acid` | `number.intellichem_cyanuric_acid` |

**Prerequisites:**
- [Pentair IntelliCenter](https://github.com/dwradcliffe/home-assistant-intellicenter) integration installed
- IntelliChem module connected to your pool system
- SpinTouch custom integration installed

**Trigger:** When SpinTouch disconnects (indicating test complete)

## Chemistry Alerts

The `chemistry_alerts.yaml` automation monitors readings and sends alerts for:

| Alert | Trigger |
|-------|---------|
| Low Chlorine | FC < 1.0 ppm |
| High Chlorine | FC > 5.0 ppm |
| pH Out of Range | pH < 7.2 or pH > 7.8 |
| Low FC/CYA Ratio | Ratio < 5% |
| High Calcium | CH > 400 ppm |
| High Phosphate | > 500 ppb |
| Salt Out of Range | < 2700 or > 3400 ppm |

Also includes a weekly summary notification on Sundays at 9 AM.

## Customization

### Entity Names

If your SpinTouch device has a different name, update the entity IDs:

```yaml
# Default format
sensor.spintouch_free_chlorine

# If you renamed your device
sensor.pool_spintouch_free_chlorine
```

### Notification Service

Replace `persistent_notification.create` with your preferred notification service:

```yaml
# Mobile app
service: notify.mobile_app_your_phone

# Telegram
service: notify.telegram

# Alexa
service: notify.alexa_media
```

### Thresholds

Adjust alert thresholds based on your pool type and preferences:

```yaml
# Salt pool with higher CYA tolerance
trigger:
  - platform: numeric_state
    entity_id: sensor.spintouch_cyanuric_acid
    above: 80  # Increased from 50
```

## Recommended Pool Chemistry Ranges

| Parameter | Min | Max | Ideal |
|-----------|-----|-----|-------|
| Free Chlorine | 1.0 ppm | 3.0 ppm | 2.0 ppm |
| pH | 7.2 | 7.8 | 7.4-7.6 |
| Total Alkalinity | 80 ppm | 120 ppm | 100 ppm |
| Calcium Hardness | 200 ppm | 400 ppm | 300 ppm |
| Cyanuric Acid | 30 ppm | 50 ppm | 40 ppm |
| Salt (SWG) | 2700 ppm | 3400 ppm | 3200 ppm |
| Phosphate | 0 ppb | 500 ppb | < 100 ppb |
| FC/CYA Ratio | 5% | - | 7.5%+ |
