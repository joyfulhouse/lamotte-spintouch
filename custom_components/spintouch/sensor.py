"""Sensor platform for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CALCULATED_SENSORS, DOMAIN, SENSORS
from .coordinator import SpinTouchCoordinator, SpinTouchData

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

    entities: list[SensorEntity] = []

    # Primary sensors from BLE data
    for sensor_def in SENSORS:
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

    # Diagnostic sensors
    entities.append(SpinTouchLastReadingSensor(coordinator=coordinator, entry=entry))

    async_add_entities(entities)


class SpinTouchSensor(CoordinatorEntity[SpinTouchCoordinator], SensorEntity):  # type: ignore[misc]
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

        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_suggested_display_precision = decimals

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="LaMotte",
            model="WaterLink Spin Touch",
        )

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
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._key in self.coordinator.data.values
        )


class SpinTouchLastReadingSensor(
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
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

        self._attr_unique_id = f"{entry.entry_id}_last_reading"
        self._attr_name = "Last Reading"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="LaMotte",
            model="WaterLink Spin Touch",
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the last reading timestamp."""
        data: SpinTouchData | None = self.coordinator.data
        if data and data.last_reading_time:
            return data.last_reading_time
        return None
