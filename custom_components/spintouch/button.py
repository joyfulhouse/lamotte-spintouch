"""Button platform for SpinTouch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .base import SpinTouchEntity
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
    """Set up SpinTouch buttons from a config entry."""
    coordinator: SpinTouchCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            SpinTouchForceReconnectButton(coordinator, entry),
        ]
    )


class SpinTouchForceReconnectButton(
    SpinTouchEntity,
    CoordinatorEntity[SpinTouchCoordinator],  # type: ignore[misc]
    ButtonEntity,  # type: ignore[misc]
):
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
        super().__init__(coordinator)
        self._setup_spintouch_device(coordinator, entry, "force_reconnect", "Force Reconnect")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_force_reconnect()
