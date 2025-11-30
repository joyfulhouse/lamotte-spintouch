"""Tests for SpinTouch config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.spintouch.config_flow import (
    SpinTouchConfigFlow,
    SpinTouchOptionsFlow,
)
from custom_components.spintouch.const import (
    CONF_DISK_SERIES,
    DEFAULT_DISK_SERIES,
    SERVICE_UUID,
)


@pytest.fixture
def mock_bluetooth_service_info() -> MagicMock:
    """Create a mock BluetoothServiceInfoBleak."""
    service_info = MagicMock()
    service_info.address = "BB:BD:05:0B:2D:1F"
    service_info.name = "SpinTouch-0B2D1F"
    service_info.service_uuids = [SERVICE_UUID]
    service_info.rssi = -60
    return service_info


class TestConfigFlow:
    """Test the config flow."""

    async def test_flow_bluetooth_discovery(
        self,
        mock_bluetooth_service_info: MagicMock,
    ) -> None:
        """Test Bluetooth discovery initiates config flow."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()
        flow.hass.config_entries.async_entries.return_value = []
        flow.context = {}

        with (
            patch.object(flow, "async_set_unique_id", return_value=None),
            patch.object(flow, "_abort_if_unique_id_configured", return_value=None),
        ):
            result = await flow.async_step_bluetooth(mock_bluetooth_service_info)

        assert result["type"] == "form"
        assert result["step_id"] == "bluetooth_confirm"
        assert "disk_series" in result["data_schema"].schema

    async def test_flow_bluetooth_confirm(
        self,
        mock_bluetooth_service_info: MagicMock,
    ) -> None:
        """Test confirming Bluetooth discovery creates entry."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()
        flow._discovery_info = mock_bluetooth_service_info

        with patch.object(flow, "async_create_entry") as mock_create:
            mock_create.return_value = {"type": "create_entry"}
            result = await flow.async_step_bluetooth_confirm(
                {CONF_DISK_SERIES: DEFAULT_DISK_SERIES}
            )

        assert result["type"] == "create_entry"
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["data"]["address"] == mock_bluetooth_service_info.address
        assert call_kwargs["data"][CONF_DISK_SERIES] == DEFAULT_DISK_SERIES

    async def test_flow_bluetooth_confirm_no_device(self) -> None:
        """Test bluetooth confirm aborts when no device info."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()
        flow._discovery_info = None

        result = await flow.async_step_bluetooth_confirm(None)

        assert result["type"] == "abort"
        assert result["reason"] == "no_device"

    async def test_flow_user_no_devices(self) -> None:
        """Test user flow when no devices discovered."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()

        with patch(
            "custom_components.spintouch.config_flow.bluetooth.async_discovered_service_info",
            return_value=[],
        ):
            result = await flow.async_step_user(None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        # Should allow manual address entry
        assert "address" in result["data_schema"].schema

    async def test_flow_user_with_devices(
        self,
        mock_bluetooth_service_info: MagicMock,
    ) -> None:
        """Test user flow when devices are discovered."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()

        with patch(
            "custom_components.spintouch.config_flow.bluetooth.async_discovered_service_info",
            return_value=[mock_bluetooth_service_info],
        ):
            result = await flow.async_step_user(None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        # Should show picker with discovered device
        assert "address" in result["data_schema"].schema

    async def test_flow_user_select_device(
        self,
        mock_bluetooth_service_info: MagicMock,
    ) -> None:
        """Test user selects a discovered device."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()
        flow._discovered_devices = {
            mock_bluetooth_service_info.address: mock_bluetooth_service_info
        }

        with (
            patch.object(flow, "async_set_unique_id", return_value=None),
            patch.object(flow, "_abort_if_unique_id_configured", return_value=None),
            patch.object(flow, "async_create_entry") as mock_create,
        ):
            mock_create.return_value = {"type": "create_entry"}
            result = await flow.async_step_user(
                {
                    "address": mock_bluetooth_service_info.address,
                    CONF_DISK_SERIES: "303",
                }
            )

        assert result["type"] == "create_entry"
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["data"]["address"] == mock_bluetooth_service_info.address
        assert call_kwargs["data"][CONF_DISK_SERIES] == "303"

    async def test_flow_user_manual_address(self) -> None:
        """Test user enters address manually."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()
        flow._discovered_devices = {}

        manual_address = "AA:BB:CC:DD:EE:FF"

        with (
            patch.object(flow, "async_set_unique_id", return_value=None),
            patch.object(flow, "_abort_if_unique_id_configured", return_value=None),
            patch.object(flow, "async_create_entry") as mock_create,
        ):
            mock_create.return_value = {"type": "create_entry"}
            result = await flow.async_step_user(
                {
                    "address": manual_address,
                    CONF_DISK_SERIES: "auto",
                }
            )

        assert result["type"] == "create_entry"
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["data"]["address"] == manual_address

    async def test_flow_reconfigure(self) -> None:
        """Test reconfigure flow."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {
            "address": "BB:BD:05:0B:2D:1F",
            CONF_DISK_SERIES: "auto",
        }
        mock_entry.title = "SpinTouch-0B2D1F"

        with patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry):
            result = await flow.async_step_reconfigure(None)

        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure"
        assert CONF_DISK_SERIES in result["data_schema"].schema

    async def test_flow_reconfigure_submit(self) -> None:
        """Test reconfigure flow submission."""
        flow = SpinTouchConfigFlow()
        flow.hass = MagicMock()

        mock_entry = MagicMock()
        mock_entry.data = {
            "address": "BB:BD:05:0B:2D:1F",
            CONF_DISK_SERIES: "auto",
        }
        mock_entry.title = "SpinTouch-0B2D1F"

        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=mock_entry),
            patch.object(flow, "async_update_reload_and_abort") as mock_update,
        ):
            mock_update.return_value = {"type": "abort"}
            await flow.async_step_reconfigure({CONF_DISK_SERIES: "303"})

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["data_updates"][CONF_DISK_SERIES] == "303"


class TestOptionsFlow:
    """Test the options flow."""

    async def test_options_flow_init(self) -> None:
        """Test options flow shows form."""
        mock_entry = MagicMock()
        mock_entry.data = {
            "address": "BB:BD:05:0B:2D:1F",
            CONF_DISK_SERIES: "auto",
        }

        flow = SpinTouchOptionsFlow(mock_entry)
        flow.hass = MagicMock()

        result = await flow.async_step_init(None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert CONF_DISK_SERIES in result["data_schema"].schema

    async def test_options_flow_submit(self) -> None:
        """Test options flow submission updates entry."""
        mock_entry = MagicMock()
        mock_entry.data = {
            "address": "BB:BD:05:0B:2D:1F",
            CONF_DISK_SERIES: "auto",
        }

        flow = SpinTouchOptionsFlow(mock_entry)
        flow.hass = MagicMock()

        result = await flow.async_step_init({CONF_DISK_SERIES: "204"})

        assert result["type"] == "create_entry"
        flow.hass.config_entries.async_update_entry.assert_called_once()
