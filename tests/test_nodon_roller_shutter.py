"""Tests for the NodOn roller shutter quirk."""

from unittest import mock

from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
from zhaquirks.nodon.roller_shutter import NodOnWindowCovering


async def test_nodon_sin_4_rs_20_entities():
    """Test the configuration entities of the NodOn SIN-4-RS-20."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "nodon-sin-4-rs-20-0x00030104.json", DEVICE_REGISTRY
        )
        ieee = device.ieee

        for unique_id in (
            "calibration_vertical_run_time_up",
            "calibration_vertical_run_time_down",
            "calibration_rotation_run_time_up",
            "calibration_rotation_run_time_down",
        ):
            number = device.get_platform_entity(
                Platform.NUMBER, unique_id=f"{ieee}-1-{unique_id}"
            )
            assert number.entity_registry_enabled_default

        device.get_platform_entity(Platform.SELECT, unique_id=f"{ieee}-1-switch_type")
        device.get_platform_entity(
            Platform.SWITCH, unique_id=f"{ieee}-1-calibration_auto_adjust"
        )
        device.get_platform_entity(
            Platform.BUTTON, unique_id=f"{ieee}-1-start_calibration"
        )
        device.get_platform_entity(
            Platform.BUTTON, unique_id=f"{ieee}-1-reset_fact_default"
        )


async def test_nodon_sin_4_rs_20_vertical_run_time():
    """Test that the vertical run times are in 10 ms steps."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "nodon-sin-4-rs-20-0x00030104.json", DEVICE_REGISTRY
        )
        window_covering = device.device.endpoints[1].window_covering
        assert isinstance(window_covering, NodOnWindowCovering)

        vertical = device.get_platform_entity(
            Platform.NUMBER,
            unique_id=f"{device.ieee}-1-calibration_vertical_run_time_up",
        )
        rotation = device.get_platform_entity(
            Platform.NUMBER,
            unique_id=f"{device.ieee}-1-calibration_rotation_run_time_up",
        )
        assert vertical.native_value == 23400
        assert vertical.native_max_value == 655350
        assert rotation.native_value == 17000

        with mock.patch.object(
            window_covering, "write_attributes", return_value=[[]]
        ) as write_attributes:
            await vertical.async_set_native_value(15000)

        assert write_attributes.call_args.args[0] == {
            "calibration_vertical_run_time_up": 1500
        }


async def test_nodon_sin_4_rs_20_start_calibration():
    """Test that the calibration button only sets the calibration bit."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "nodon-sin-4-rs-20-0x00030104.json", DEVICE_REGISTRY
        )
        window_covering = device.device.endpoints[1].window_covering
        mode_attr = WindowCovering.AttributeDefs.window_covering_mode
        mode = (
            WindowCovering.WindowCoveringMode.Motor_direction_reversed
            | WindowCovering.WindowCoveringMode.LEDs_display_feedback
        )
        window_covering._update_attribute(mode_attr.id, mode)

        button = device.get_platform_entity(
            Platform.BUTTON, unique_id=f"{device.ieee}-1-start_calibration"
        )
        with (
            mock.patch.object(
                window_covering, "read_attributes", return_value=({}, {})
            ) as read_attributes,
            mock.patch.object(
                window_covering, "write_attributes", return_value=[[]]
            ) as write_attributes,
        ):
            await button.async_press()

        assert read_attributes.call_args.args[0] == [mode_attr.id]
        assert write_attributes.call_args.args[0] == {
            mode_attr.id: mode
            | WindowCovering.WindowCoveringMode.Run_in_calibration_mode
        }


async def test_nodon_sin_4_rs_20_factory_reset():
    """Test that the factory reset button sends the Basic reset command."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "nodon-sin-4-rs-20-0x00030104.json", DEVICE_REGISTRY
        )
        basic = device.device.endpoints[1].basic

        button = device.get_platform_entity(
            Platform.BUTTON, unique_id=f"{device.ieee}-1-reset_fact_default"
        )
        with mock.patch.object(basic, "request", return_value=[0x00, 0x00]) as request:
            await button.async_press()

        assert (
            request.call_args.args[1] == Basic.ServerCommandDefs.reset_fact_default.id
        )
