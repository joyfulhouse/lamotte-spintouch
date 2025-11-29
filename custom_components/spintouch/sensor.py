"""Sensor platform for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import SpinTouchEntity
from .const import (
    CALCULATED_SENSORS,
    CONF_DISK_SERIES,
    DEFAULT_DISK_SERIES,
    DOMAIN,
    SENSORS,
)
from .coordinator import SpinTouchCoordinator, SpinTouchData
from .util import restore_datetime_state, restore_float_state

# Short display names for water quality status
PARAMETER_SHORT_NAMES: dict[str, str] = {
    "free_chlorine": "FC",
    "total_chlorine": "TC",
    "bromine": "Br",
    "ph": "pH",
    "alkalinity": "Alk",
    "calcium": "Ca",
    "cyanuric_acid": "CYA",
    "copper": "Cu",
    "iron": "Fe",
    "phosphate": "Phos",
    "borate": "Bor",
    "salt": "Salt",
}

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpinTouch sensors from a config entry."""
    coordinator: SpinTouchCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Determine disk series (auto-detected or configured)
    configured_disk_series = entry.data.get(CONF_DISK_SERIES, DEFAULT_DISK_SERIES)
    disk_series = (
        coordinator.data.detected_disk_series
        if coordinator.data and coordinator.data.detected_disk_series
        else configured_disk_series
    )

    # Determine which sensors to skip based on disk series
    skip_sensors = _get_skip_sensors(disk_series)

    entities: list[SensorEntity] = []

    # Primary sensors from BLE data
    for sensor_def in SENSORS:
        if sensor_def.key not in skip_sensors:
            entities.append(
                SpinTouchSensor(
                    coordinator=coordinator,
                    entry=entry,
                    key=sensor_def.key,
                    name=sensor_def.name,
                    unit=sensor_def.unit,
                    icon=sensor_def.icon,
                    decimals=sensor_def.decimals,
                )
            )

    # Calculated sensors
    for calc_sensor in CALCULATED_SENSORS:
        entities.append(
            SpinTouchSensor(
                coordinator=coordinator,
                entry=entry,
                key=calc_sensor.key,
                name=calc_sensor.name,
                unit=calc_sensor.unit,
                icon=calc_sensor.icon,
                decimals=calc_sensor.decimals,
            )
        )

    # Diagnostic and status sensors
    entities.extend(
        [
            SpinTouchLastReadingSensor(coordinator=coordinator, entry=entry),
            SpinTouchReportTimeSensor(coordinator=coordinator, entry=entry),
            SpinTouchWaterQualitySensor(coordinator=coordinator, entry=entry),
        ]
    )

    async_add_entities(entities)


def _get_skip_sensors(disk_series: str) -> set[str]:
    """Get sensors to skip based on disk series.

    Disk 203/204: Have Phosphate (0x0E)
    Disk 303/304: Have Borate (0x0D), no Phosphate
    """
    if disk_series in ("303", "304"):
        return {"phosphate"}
    if disk_series in ("203", "204"):
        return {"borate"}
    return set()


class SpinTouchSensor(
    SpinTouchEntity,
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    RestoreEntity,  # type: ignore[misc]
    SensorEntity,  # type: ignore[misc]
):
    """Sensor for SpinTouch water quality parameters."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        unit: str | None,
        icon: str,
        decimals: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._decimals = decimals

        self._setup_spintouch_device(coordinator, entry, key, name)
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_suggested_display_precision = decimals

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()

        restored_value = await restore_float_state(self)
        if (
            restored_value is not None
            and self.coordinator.data
            and self._key not in self.coordinator.data.values
        ):
            self.coordinator.data.values[self._key] = restored_value

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data:
            value = self.coordinator.data.values.get(self._key)
            return float(value) if value is not None else None
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.data is not None and self._key in self.coordinator.data.values


class SpinTouchLastReadingSensor(
    SpinTouchEntity,
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    RestoreEntity,  # type: ignore[misc]
    SensorEntity,  # type: ignore[misc]
):
    """Sensor showing the last reading timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._setup_spintouch_device(coordinator, entry, "last_reading", "Last Reading")

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()

        restored_dt = await restore_datetime_state(self)
        if restored_dt and self.coordinator.data and not self.coordinator.data.last_reading_time:
            self.coordinator.data.last_reading_time = restored_dt

    @property
    def native_value(self) -> datetime | None:
        """Return the last reading timestamp."""
        data: SpinTouchData | None = self.coordinator.data
        return data.last_reading_time if data else None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.data is not None
            and self.coordinator.data.last_reading_time is not None
        )


class SpinTouchReportTimeSensor(
    SpinTouchEntity,
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    RestoreEntity,  # type: ignore[misc]
    SensorEntity,  # type: ignore[misc]
):
    """Sensor showing the test report timestamp from SpinTouch device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clipboard-clock-outline"

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._setup_spintouch_device(coordinator, entry, "report_time", "Report Time")

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()

        restored_dt = await restore_datetime_state(self)
        if restored_dt and self.coordinator.data and not self.coordinator.data.report_time:
            self.coordinator.data.report_time = restored_dt

    @property
    def native_value(self) -> datetime | None:
        """Return the report timestamp from SpinTouch."""
        data: SpinTouchData | None = self.coordinator.data
        return data.report_time if data else None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.data is not None and self.coordinator.data.report_time is not None


class SpinTouchWaterQualitySensor(
    SpinTouchEntity,
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    SensorEntity,  # type: ignore[misc]
):
    """Sensor showing overall water quality status."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:water-check"

    # Ideal ranges for pool water (min, max)
    RANGES: ClassVar[dict[str, tuple[float, float]]] = {
        "free_chlorine": (1.0, 3.0),
        "ph": (7.2, 7.6),
        "alkalinity": (80, 120),
        "calcium": (200, 400),
        "cyanuric_acid": (30, 50),
        "iron": (0, 0.3),
        "phosphate": (0, 100),
    }

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._setup_spintouch_device(coordinator, entry, "water_quality", "Water Quality")

    def _get_issues(self) -> dict[str, dict[str, Any]]:
        """Get all parameters that are out of range."""
        issues: dict[str, dict[str, Any]] = {}

        if not self.coordinator.data or not self.coordinator.data.values:
            return issues

        for key, (min_val, max_val) in self.RANGES.items():
            value = self.coordinator.data.values.get(key)
            if value is not None:
                if value < min_val:
                    issues[key] = {
                        "value": value,
                        "status": "low",
                        "min": min_val,
                        "max": max_val,
                    }
                elif value > max_val:
                    issues[key] = {
                        "value": value,
                        "status": "high",
                        "min": min_val,
                        "max": max_val,
                    }

        return issues

    @property
    def native_value(self) -> str:
        """Return water quality status."""
        issues = self._get_issues()

        if not issues:
            return "OK"

        # Build list of short names with direction indicator
        problem_names = [
            f"{PARAMETER_SHORT_NAMES.get(key, key)} {'↓' if info['status'] == 'low' else '↑'}"
            for key, info in issues.items()
        ]

        return ", ".join(problem_names)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed information about water quality."""
        issues = self._get_issues()

        attributes: dict[str, Any] = {"issues_count": len(issues)}

        if issues:
            attributes["issues"] = {
                key: {
                    "value": info["value"],
                    "status": info["status"],
                    "target_range": f"{info['min']}-{info['max']}",
                }
                for key, info in issues.items()
            }

        return attributes

    @property
    def icon(self) -> str:
        """Return icon based on water quality status."""
        issues = self._get_issues()
        if not issues:
            return "mdi:water-check"
        if len(issues) >= 3:
            return "mdi:water-alert"
        return "mdi:water-remove"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.data is not None and bool(self.coordinator.data.values)
