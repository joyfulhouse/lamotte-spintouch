"""Button platform for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SpinTouchCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SpinTouch buttons from a config entry."""
    coordinator: SpinTouchCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            SpinTouchForceReconnectButton(coordinator, entry),
        ]
    )


class SpinTouchForceReconnectButton(ButtonEntity):  # type: ignore[misc]
    """Button to force reconnection to SpinTouch."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-connect"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: SpinTouchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        self._coordinator = coordinator

        self._attr_unique_id = f"{entry.entry_id}_force_reconnect"
        self._attr_name = "Force Reconnect"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="LaMotte",
            model="WaterLink Spin Touch",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._coordinator.async_force_reconnect()
