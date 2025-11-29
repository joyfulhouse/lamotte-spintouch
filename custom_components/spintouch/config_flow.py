"""Config flow for LaMotte WaterLink Spin Touch integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DEVICE_NAME_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SpinTouchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SpinTouch."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the Bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        assert self._discovery_info is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name,
                data={},
            )

        self._set_confirm_only()
        placeholders = {"name": self._discovery_info.name}
        self.context["title_placeholders"] = placeholders

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=placeholders,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick a device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address.upper(), raise_on_progress=False)
            self._abort_if_unique_id_configured()

            # Check if it's a discovered device or manual entry
            if address in self._discovered_devices:
                title = self._discovered_devices[address].name
            else:
                title = f"SpinTouch ({address.upper()})"

            return self.async_create_entry(
                title=title,
                data={CONF_ADDRESS: address.upper()},
            )

        # Discover SpinTouch devices
        current_addresses = self._async_current_ids()

        for discovery_info in async_discovered_service_info(self.hass, connectable=True):
            if discovery_info.address in current_addresses:
                continue
            if (
                discovery_info.name
                and discovery_info.name.startswith(DEVICE_NAME_PREFIX)
            ):
                self._discovered_devices[discovery_info.address] = discovery_info

        # If devices found, show picker. Otherwise show manual entry.
        if self._discovered_devices:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): vol.In(
                            {
                                address: f"{info.name} ({address})"
                                for address, info in self._discovered_devices.items()
                            }
                        ),
                    }
                ),
            )

        # No devices found - allow manual MAC address entry
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                }
            ),
            description_placeholders={
                "example": "AA:BB:CC:DD:EE:FF",
            },
        )
