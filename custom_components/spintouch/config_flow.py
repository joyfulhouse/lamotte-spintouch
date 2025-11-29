"""Config flow for LaMotte WaterLink Spin Touch integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, SERVICE_UUID

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)


class SpinTouchConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
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
        _LOGGER.debug("Bluetooth discovery: %s", discovery_info.address)

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info

        # Use device name if available, otherwise generate one
        name = discovery_info.name or f"SpinTouch {discovery_info.address[-8:].replace(':', '')}"

        self.context["title_placeholders"] = {"name": name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if self._discovery_info is None:
            return self.async_abort(reason="no_device")

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name
                or f"SpinTouch {self._discovery_info.address[-8:].replace(':', '')}",
                data={CONF_ADDRESS: self._discovery_info.address},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or "SpinTouch",
                "address": self._discovery_info.address,
            },
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step - manual setup or pick from discovered devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]

            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            # Check if device is reachable
            if address in self._discovered_devices:
                return self.async_create_entry(
                    title=self._discovered_devices[address].name
                    or f"SpinTouch {address[-8:].replace(':', '')}",
                    data={CONF_ADDRESS: address},
                )
            else:
                # Manual entry - create anyway
                return self.async_create_entry(
                    title=f"SpinTouch {address[-8:].replace(':', '')}",
                    data={CONF_ADDRESS: address},
                )

        # Scan for SpinTouch devices
        self._discovered_devices = {}
        for service_info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            # Check for SpinTouch service UUID
            if SERVICE_UUID.lower() in [uuid.lower() for uuid in service_info.service_uuids]:
                self._discovered_devices[service_info.address] = service_info

        if self._discovered_devices:
            # Show picker for discovered devices
            addresses = {
                addr: f"{info.name or 'SpinTouch'} ({addr})"
                for addr, info in self._discovered_devices.items()
            }
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(addresses)}),
                errors=errors,
            )
        else:
            # No devices found - allow manual entry
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): str,
                    }
                ),
                errors=errors,
                description_placeholders={"no_devices": "true"},
            )
