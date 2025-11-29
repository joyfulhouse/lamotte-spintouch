"""The LaMotte WaterLink Spin Touch integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SpinTouchCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LaMotte WaterLink Spin Touch from a config entry."""
    # Get address from config data or unique_id (for backwards compatibility)
    address: str = entry.data.get(CONF_ADDRESS) or entry.unique_id
    if not address:
        _LOGGER.error("No address configured for SpinTouch")
        return False

    address = address.upper()
    _LOGGER.debug("Setting up SpinTouch with address: %s", address)

    coordinator = SpinTouchCoordinator(hass, address, entry)

    # Don't require immediate connection - device may not be advertising
    # The coordinator will connect on-demand during updates
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: SpinTouchCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_disconnect()

    return unload_ok
