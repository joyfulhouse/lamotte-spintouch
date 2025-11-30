"""Binary sensor platform for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import SpinTouchEntity
from .coordinator import SpinTouchCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import SpinTouchConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SpinTouchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpinTouch binary sensors from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            SpinTouchConnectedSensor(coordinator, entry),
            SpinTouchConnectionEnabledSensor(coordinator, entry),
        ]
    )


class SpinTouchConnectedSensor(
    SpinTouchEntity,
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
        entry: SpinTouchConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._setup_spintouch_device(coordinator, entry, "connected", "Connected")

    @property
    def is_on(self) -> bool:
        """Return True if connected."""
        return self.coordinator.data.connected if self.coordinator.data else False


class SpinTouchConnectionEnabledSensor(
    SpinTouchEntity,
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
        entry: SpinTouchConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._setup_spintouch_device(coordinator, entry, "connection_enabled", "Connection Enabled")

    @property
    def is_on(self) -> bool:
        """Return True if connection is enabled."""
        return self.coordinator.data.connection_enabled if self.coordinator.data else True
