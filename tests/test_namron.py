"""Tests for Namron quirks."""

from pathlib import Path
from unittest import mock

from zha.quirks import DEVICE_REGISTRY, QuirkRegistryEntry
from zha.zigbee.cluster_config import aggregate_cluster_configs
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.hvac import TemperatureDisplayMode, Thermostat, UserInterface

from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.namron.namron_4512783 import (
    NamronScreenOnTime,
    NamronSensorMode,
    NamronThermostatCluster,
    NamronWorkDays,
)

THERMOSTAT_ENTITY_SUFFIXES = {
    "anti_frost",
    "automatic_time",
    "fault",
    "holiday_temperature",
    "operation_mode",
    "panel_brightness",
    "regulator_cycle",
    "regulator_percentage",
    "screen_on_time",
    "vacation_mode",
    "window_open_check",
    "window_state",
    "work_days",
    "max_heat_temperature",
}
ENTITY_SUFFIXES = THERMOSTAT_ENTITY_SUFFIXES | {"temperature_display_mode"}


def _get_quirk_entry() -> QuirkRegistryEntry:
    """Return the Namron 4512783 quirk registry entry."""
    entries = [
        entry
        for entry in DEVICE_REGISTRY
        if isinstance(entry.zha_device_factory, QuirkV2Factory)
        and Path(entry.source.file).name == "namron_4512783.py"
    ]
    assert len(entries) == 1
    return entries[0]


def _get_quirked_device(zigpy_device_from_v2_quirk):
    """Create a Namron 4512783 with its thermostat cluster."""
    return zigpy_device_from_v2_quirk(
        manufacturer="Namron AS",
        model="4512783",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                UserInterface.cluster_id: ClusterType.Server,
            }
        },
    )


def test_namron_4512783_entities(zigpy_device_from_v2_quirk):
    """Test cluster replacement, entity discovery, and startup reads."""
    device = _get_quirked_device(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[1].thermostat
    assert type(cluster) is NamronThermostatCluster

    attrs = cluster.AttributeDefs
    expected_types = {
        "window_open_check": t.Bool,
        "anti_frost": t.Bool,
        "window_state": t.Bool,
        "work_days": NamronWorkDays,
        "sensor_mode": NamronSensorMode,
        "panel_brightness": t.uint8_t,
        "fault": t.bitmap8,
        "regulator_cycle": t.uint8_t,
        "holiday_temperature": t.int16s,
        "regulator_percentage": t.int16s,
        "vacation_mode": t.Bool,
        "automatic_time": t.Bool,
        "max_heat_temperature": t.int16s,
        "screen_on_time": NamronScreenOnTime,
    }
    for attribute_name, expected_type in expected_types.items():
        attribute = getattr(attrs, attribute_name)
        assert attribute.type is expected_type
        assert attribute.manufacturer_code is None

    cluster.update_attribute(attrs.window_open_check.id, t.Bool.true)
    cluster.update_attribute(attrs.anti_frost.id, t.Bool.false)
    cluster.update_attribute(attrs.window_state.id, t.Bool.false)
    cluster.update_attribute(
        attrs.work_days.id, NamronWorkDays.Monday_Friday_Saturday_Sunday
    )
    cluster.update_attribute(attrs.sensor_mode.id, NamronSensorMode.Regulator)
    cluster.update_attribute(attrs.panel_brightness.id, 80)
    cluster.update_attribute(attrs.fault.id, t.bitmap8(0))
    cluster.update_attribute(attrs.regulator_cycle.id, 2)
    cluster.update_attribute(attrs.holiday_temperature.id, 500)
    cluster.update_attribute(attrs.regulator_percentage.id, 20)
    cluster.update_attribute(attrs.vacation_mode.id, t.Bool.false)
    cluster.update_attribute(attrs.automatic_time.id, t.Bool.true)
    cluster.update_attribute(attrs.max_heat_temperature.id, 350)
    cluster.update_attribute(attrs.screen_on_time.id, NamronScreenOnTime.Thirty_seconds)
    device.endpoints[1].thermostat_ui.update_attribute(
        UserInterface.AttributeDefs.temperature_display_mode.id,
        TemperatureDisplayMode.Metric,
    )

    gateway = mock.Mock()
    gateway.config.config.device_options.consider_unavailable_mains = 900
    gateway.config.config.device_options.consider_unavailable_battery = 900
    zha_device = _get_quirk_entry().zha_device_factory(device, gateway)
    entities = {
        entity.unique_id.rsplit("-", 1)[-1]: entity
        for entity in zha_device.discover_entities()
        if entity.unique_id.rsplit("-", 1)[-1] in ENTITY_SUFFIXES
    }

    assert set(entities) == ENTITY_SUFFIXES
    assert entities["work_days"].options == [
        "Monday Friday Saturday Sunday",
        "Monday Saturday Sunday",
        "No time off",
        "Time off",
    ]
    assert entities["operation_mode"].options == [
        "Internal air sensor",
        "Floor sensor",
        "Internal air with floor limit",
        "External room sensor",
        "External room with floor limit",
        "Floor sensor with regulator",
        "Regulator",
    ]
    assert entities["operation_mode"].current_option == "Regulator"
    assert entities["screen_on_time"].options == [
        "Always on",
        "Ten seconds",
        "Thirty seconds",
        "Sixty seconds",
    ]
    assert entities["screen_on_time"].current_option == "Thirty seconds"
    assert entities["temperature_display_mode"].options == ["Metric", "Imperial"]
    assert entities["temperature_display_mode"].current_option == "Metric"
    assert entities["panel_brightness"].native_value == 80
    assert entities["regulator_cycle"].native_value == 2
    assert entities["holiday_temperature"].native_value == 5
    assert entities["regulator_percentage"].native_value == 20
    assert entities["max_heat_temperature"].native_value == 35
    assert entities["fault"].native_value == 0
    assert all(entity.is_supported() for entity in entities.values())

    configs = aggregate_cluster_configs(entities.values())
    thermostat_config = configs[(1, Thermostat.cluster_id, True)]
    assert thermostat_config.bind is False
    assert set(thermostat_config.attributes) == {
        "anti_frost",
        "automatic_time",
        "fault",
        "holiday_temperature",
        "max_heat_temperature",
        "panel_brightness",
        "regulator_cycle",
        "regulator_percentage",
        "screen_on_time",
        "sensor_mode",
        "vacation_mode",
        "window_open_check",
        "window_state",
        "work_days",
    }
    user_interface_config = configs[(1, UserInterface.cluster_id, True)]
    assert user_interface_config.bind is False
    assert set(user_interface_config.attributes) == {"temperature_display_mode"}
    for config in (thermostat_config, user_interface_config):
        assert all(
            attribute.read_on_startup for attribute in config.attributes.values()
        )
        assert all(
            attribute.reporting is None for attribute in config.attributes.values()
        )


async def test_namron_4512783_writes(zigpy_device_from_v2_quirk):
    """Test attribute types and standard non-manufacturer framing."""
    device = _get_quirked_device(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[1].thermostat
    cluster.endpoint.request = mock.AsyncMock(return_value=[0])

    await cluster.write_attributes(
        {
            "window_open_check": t.Bool.true,
            "anti_frost": t.Bool.false,
            "work_days": NamronWorkDays.Monday_Friday_Saturday_Sunday,
            "sensor_mode": NamronSensorMode.Regulator,
            "panel_brightness": 80,
            "regulator_cycle": 2,
            "holiday_temperature": 500,
            "regulator_percentage": 20,
            "automatic_time": t.Bool.true,
            "max_heat_temperature": 350,
            "screen_on_time": NamronScreenOnTime.Thirty_seconds,
        }
    )

    request = cluster.endpoint.request.await_args
    assert request is not None
    assert request.kwargs.get("manufacturer") is None
    header, payload = foundation.ZCLHeader.deserialize(request.kwargs["data"])
    assert not header.frame_control.is_manufacturer_specific
    command, remaining = foundation.GENERAL_COMMANDS[
        header.command_id
    ].schema.deserialize(payload)
    assert remaining == b""
    assert [
        (attribute.attrid, attribute.value.type, attribute.value.value)
        for attribute in command.attributes
    ] == [
        (0x8000, foundation.DataTypeId.bool_, t.Bool.true),
        (0x8001, foundation.DataTypeId.bool_, t.Bool.false),
        (0x8003, foundation.DataTypeId.enum8, 0),
        (0x8004, foundation.DataTypeId.enum8, 6),
        (0x8005, foundation.DataTypeId.uint8, 80),
        (0x8007, foundation.DataTypeId.uint8, 2),
        (0x8013, foundation.DataTypeId.int16, 500),
        (0x801D, foundation.DataTypeId.int16, 20),
        (0x8022, foundation.DataTypeId.bool_, t.Bool.true),
        (0x8025, foundation.DataTypeId.int16, 350),
        (0x8029, foundation.DataTypeId.enum8, 2),
    ]

    user_interface = device.endpoints[1].thermostat_ui
    cluster.endpoint.request.reset_mock()
    await user_interface.write_attributes(
        {"temperature_display_mode": TemperatureDisplayMode.Imperial}
    )
    request = cluster.endpoint.request.await_args
    assert request is not None
    assert request.kwargs.get("manufacturer") is None
    header, payload = foundation.ZCLHeader.deserialize(request.kwargs["data"])
    assert not header.frame_control.is_manufacturer_specific
    command, remaining = foundation.GENERAL_COMMANDS[
        header.command_id
    ].schema.deserialize(payload)
    assert remaining == b""
    assert [
        (attribute.attrid, attribute.value.type, attribute.value.value)
        for attribute in command.attributes
    ] == [(0x0000, foundation.DataTypeId.enum8, 1)]
