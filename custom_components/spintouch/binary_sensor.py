"""Binary sensor platform for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SpinTouchCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpinTouch binary sensors from a config entry."""
    coordinator: SpinTouchCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [
        SpinTouchConnectedSensor(coordinator, entry),
        SpinTouchConnectionEnabledSensor(coordinator, entry),
        SpinTouchProblemSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class SpinTouchConnectedSensor(
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    BinarySensorEntity,  # type: ignore[misc]
):
    """Binary sensor showing connection status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{entry.entry_id}_connected"
        self._attr_name = "Connected"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="LaMotte",
            model="WaterLink Spin Touch",
        )

    @property
    def is_on(self) -> bool:
        """Return True if connected."""
        return self.coordinator.data.connected if self.coordinator.data else False


class SpinTouchConnectionEnabledSensor(
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    BinarySensorEntity,  # type: ignore[misc]
):
    """Binary sensor showing if connection is enabled (not in reconnect delay)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bluetooth-settings"

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{entry.entry_id}_connection_enabled"
        self._attr_name = "Connection Enabled"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="LaMotte",
            model="WaterLink Spin Touch",
        )

    @property
    def is_on(self) -> bool:
        """Return True if connection is enabled."""
        return self.coordinator.data.connection_enabled if self.coordinator.data else True


class SpinTouchProblemSensor(
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    BinarySensorEntity,  # type: ignore[misc]
):
    """Binary sensor showing if any parameter is out of range."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    # Ideal ranges for pool water
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

        self._attr_unique_id = f"{entry.entry_id}_problem"
        self._attr_name = "Water Quality Problem"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="LaMotte",
            model="WaterLink Spin Touch",
        )

    @property
    def is_on(self) -> bool:
        """Return True if any parameter is out of range (problem detected)."""
        if not self.coordinator.data or not self.coordinator.data.values:
            return False

        for key, (min_val, max_val) in self.RANGES.items():
            value = self.coordinator.data.values.get(key)
            if value is not None and (value < min_val or value > max_val):
                return True

        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return which parameters are out of range."""
        if not self.coordinator.data or not self.coordinator.data.values:
            return {}

        out_of_range: list[str] = []
        for key, (min_val, max_val) in self.RANGES.items():
            value = self.coordinator.data.values.get(key)
            if value is not None:
                if value < min_val:
                    out_of_range.append(f"{key}: {value} (low, min={min_val})")
                elif value > max_val:
                    out_of_range.append(f"{key}: {value} (high, max={max_val})")

        return {"out_of_range": out_of_range} if out_of_range else {}
