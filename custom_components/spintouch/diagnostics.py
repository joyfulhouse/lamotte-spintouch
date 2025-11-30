"""Diagnostics support for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import SpinTouchConfigEntry

# Keys to redact from diagnostics output
TO_REDACT = {"address", "unique_id"}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    entry: SpinTouchConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    # Build sensor values dict, handling None values
    sensor_values: dict[str, float | None] = {}
    if data and data.values:
        sensor_values = dict(data.values)

    # Build diagnostics data
    diagnostics_data: dict[str, Any] = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "device": {
            "address": "**REDACTED**",
            "name": coordinator.device_name,
            "connected": data.connected if data else False,
            "connection_enabled": data.connection_enabled if data else True,
        },
        "data": {
            "sensor_values": sensor_values,
            "last_reading_time": (
                data.last_reading_time.isoformat() if data and data.last_reading_time else None
            ),
            "report_time": data.report_time.isoformat() if data and data.report_time else None,
            "detected_param_ids": (
                [hex(pid) for pid in sorted(data.detected_param_ids)]
                if data and data.detected_param_ids
                else []
            ),
            "num_valid_results": data.num_valid_results if data else 0,
            "disk_type": data.disk_type if data else None,
            "disk_type_index": data.disk_type_index if data else None,
            "sanitizer_type": data.sanitizer_type if data else None,
            "sanitizer_type_index": data.sanitizer_type_index if data else None,
            "detected_disk_series": data.detected_disk_series if data else None,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": (
                str(coordinator.update_interval) if coordinator.update_interval else None
            ),
        },
    }

    return diagnostics_data
