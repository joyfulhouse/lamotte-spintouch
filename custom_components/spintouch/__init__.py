"""The LaMotte WaterLink Spin Touch integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothScanningMode
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from homeassistant.const import CONF_ADDRESS, Platform

from .const import DOMAIN
from .coordinator import SpinTouchCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SpinTouch from a config entry."""
    address: str = entry.data[CONF_ADDRESS]

    _LOGGER.info("Setting up SpinTouch at %s", address)

    # Get initial service info if device is currently visible
    service_info = bluetooth.async_last_service_info(hass, address, connectable=True)

    coordinator = SpinTouchCoordinator(hass, address, service_info)

    # Register for Bluetooth callbacks when device is seen
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            coordinator.async_handle_bluetooth_event,
            BluetoothCallbackMatcher({ADDRESS: address}),
            BluetoothScanningMode.ACTIVE,
        )
    )

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initial connection attempt
    await coordinator.async_connect()

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading SpinTouch entry %s", entry.entry_id)

    # Disconnect from device
    coordinator: SpinTouchCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_disconnect()

    # Unload platforms
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
