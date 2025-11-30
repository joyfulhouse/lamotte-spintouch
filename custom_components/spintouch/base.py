"""Base entity classes and mixins for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from . import SpinTouchConfigEntry
    from .coordinator import SpinTouchCoordinator

# Device info constants
MANUFACTURER = "LaMotte"
MODEL = "WaterLink Spin Touch"


class SpinTouchEntity:
    """Mixin providing common SpinTouch entity setup.

    This mixin should be used with CoordinatorEntity (or any entity that has
    a coordinator attribute) to provide consistent device info across all entities.
    """

    # Type hints for attributes set by _setup_spintouch_device
    # Using Any to avoid conflicts with Entity base class definitions
    _attr_unique_id: Any
    _attr_name: Any
    _attr_device_info: Any

    def _setup_spintouch_device(
        self,
        coordinator: SpinTouchCoordinator,
        entry: SpinTouchConfigEntry,
        key: str,
        name: str,
    ) -> None:
        """Set up common SpinTouch entity attributes.

        Args:
            coordinator: The SpinTouch coordinator instance.
            entry: The config entry for this device.
            key: Unique key for this entity (e.g., "free_chlorine", "connected").
            name: Display name for this entity.
        """
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
