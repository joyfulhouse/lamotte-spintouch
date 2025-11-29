"""Sensor platform for LaMotte WaterLink Spin Touch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_PARTS_PER_BILLION, CONCENTRATION_PARTS_PER_MILLION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SpinTouchCoordinator, SpinTouchData


@dataclass(frozen=True, kw_only=True)
class SpinTouchSensorEntityDescription(SensorEntityDescription):
    """Describes a SpinTouch sensor entity."""

    value_fn: Callable[[SpinTouchData], float | datetime | None]


SENSOR_DESCRIPTIONS: tuple[SpinTouchSensorEntityDescription, ...] = (
    SpinTouchSensorEntityDescription(
        key="free_chlorine",
        translation_key="free_chlorine",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flask",
        suggested_display_precision=2,
        value_fn=lambda data: data.free_chlorine,
    ),
    SpinTouchSensorEntityDescription(
        key="total_chlorine",
        translation_key="total_chlorine",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flask",
        suggested_display_precision=2,
        value_fn=lambda data: data.total_chlorine,
    ),
    SpinTouchSensorEntityDescription(
        key="ph",
        translation_key="ph",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:ph",
        suggested_display_precision=2,
        value_fn=lambda data: data.ph,
    ),
    SpinTouchSensorEntityDescription(
        key="alkalinity",
        translation_key="alkalinity",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water",
        suggested_display_precision=1,
        value_fn=lambda data: data.alkalinity,
    ),
    SpinTouchSensorEntityDescription(
        key="calcium_hardness",
        translation_key="calcium_hardness",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water",
        suggested_display_precision=1,
        value_fn=lambda data: data.calcium_hardness,
    ),
    SpinTouchSensorEntityDescription(
        key="cyanuric_acid",
        translation_key="cyanuric_acid",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shield-sun",
        suggested_display_precision=1,
        value_fn=lambda data: data.cyanuric_acid,
    ),
    SpinTouchSensorEntityDescription(
        key="salt",
        translation_key="salt",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shaker",
        suggested_display_precision=0,
        value_fn=lambda data: data.salt,
    ),
    SpinTouchSensorEntityDescription(
        key="iron",
        translation_key="iron",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:iron",
        suggested_display_precision=3,
        value_fn=lambda data: data.iron,
    ),
    SpinTouchSensorEntityDescription(
        key="phosphate",
        translation_key="phosphate",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_BILLION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:leaf",
        suggested_display_precision=1,
        value_fn=lambda data: data.phosphate,
    ),
    SpinTouchSensorEntityDescription(
        key="last_test_time",
        translation_key="last_test_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        value_fn=lambda data: data.last_test_time,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpinTouch sensors from a config entry."""
    coordinator: SpinTouchCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        SpinTouchSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class SpinTouchSensor(CoordinatorEntity[SpinTouchCoordinator], SensorEntity):
    """Representation of a SpinTouch sensor."""

    entity_description: SpinTouchSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        description: SpinTouchSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def native_value(self) -> float | datetime | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
