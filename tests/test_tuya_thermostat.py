"""Tests for Tuya Thermostat."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.tuya import TUYA_MCU_VERSION_RSP, TUYA_QUERY_DATA, TuyaDPType
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()

ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6d\x82"
ZCL_TUYA_SET_TIME = b"\x09\x12\x24\x0d\x00"


@pytest.mark.parametrize(
    "manuf,msg,attr,value",
    [
        (
            "_TZE204_p3lqqy2r",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE204_p3lqqy2r",
            b"\t\x16\x02\x00\t\x18\x02\x00\x04\x00\x00\x00\x18",
            Thermostat.AttributeDefs.local_temperature,
            2400,
        ),  # Current temp 24, dp 24
        (
            "_TZE204_p3lqqy2r",
            b"\t\x15\x02\x00\x08\x10\x02\x00\x04\x00\x00\x00\x19",
            Thermostat.AttributeDefs.occupied_heating_setpoint,
            2500,
        ),  # Setpoint to 25, dp 16
        (
            "_TZE204_p3lqqy2r",
            b"\t\x1c\x02\x00\x0fh\x01\x00\x01\x01",
            Thermostat.AttributeDefs.running_state,
            Thermostat.RunningState.Heat_State_On,
        ),  # Running state, dp 104
        (
            "_TZE204_p3lqqy2r",
            b"\t\x1d\x02\x00\x10k\x02\x00\x04\x00\x00\x00\x1b",
            Thermostat.AttributeDefs.max_heat_setpoint_limit,
            2700,
        ),  # Max heat set point, dp 107
        (
            "_TZE204_lzriup1j",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE284_aaeaifez",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE284_aaeaifez",
            b"\t\x15\x02\x00\x08\x02\x02\x00\x04\x00\x00\x00\xd2",
            Thermostat.AttributeDefs.occupied_heating_setpoint,
            2100,
        ),  # Setpoint to 21, dp 2
        (
            "_TZE284_aaeaifez",
            b"\t\x16\x02\x00\x09\x03\x02\x00\x04\x00\x00\x00\xf9",
            Thermostat.AttributeDefs.local_temperature,
            2490,
        ),  # Current temp 24.9, dp 3
        (
            "_TZE200_viy9ihs7",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE204_xnbkhhdr",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE284_xnbkhhdr",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE204_cvub6xbb",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
        (
            "_TZE284_cvub6xbb",
            b"\t\x13\x02\x00\x06\x01\x01\x00\x01\x01",
            Thermostat.AttributeDefs.system_mode,
            Thermostat.SystemMode.Heat,
        ),  # Set to heat, dp 1
    ],
)
async def test_handle_get_data(zigpy_device_from_v2_quirk, manuf, msg, attr, value):
    """Test handle_get_data for multiple attributes."""

    quirked = zigpy_device_from_v2_quirk(manuf, "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.thermostat is not None
    assert isinstance(ep.thermostat, Thermostat)

    thermostat_listener = ClusterListener(ep.thermostat)

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(thermostat_listener.attribute_updates) == 1
    assert thermostat_listener.attribute_updates[0][0] == attr.id
    assert thermostat_listener.attribute_updates[0][1] == value

    assert ep.thermostat.get(attr.id) == value


async def test_tuya_no_mcu_version(zigpy_device_from_v2_quirk):
    """Test lack of TUYA_MCU_VERSION_RSP messages."""

    tuya_device = zigpy_device_from_v2_quirk("_TZE284_xnbkhhdr", "TS0601")

    tuya_cluster = tuya_device.endpoints[1].tuya_manufacturer
    cluster_listener = ClusterListener(tuya_cluster)

    assert len(cluster_listener.attribute_updates) == 0

    # simulate a TUYA_MCU_VERSION_RSP message
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VERSION_RSP)
    assert hdr.command_id == TUYA_MCU_VERSION_RSP

    tuya_cluster.handle_message(hdr, args)
    assert len(cluster_listener.attribute_updates) == 0


@pytest.mark.parametrize(
    "manuf,msg,dp_id,value",
    [
        (
            "_TZE204_p3lqqy2r",
            b"\t\x1d\x02\x00\x10\x1c\x02\x00\x04\xff\xff\xff\xf7",
            28,
            -9,
        ),  # Local temp calibration to -2, dp 28
        (
            "_TZE204_lzriup1j",
            b"\t\x1d\x02\x00\x10\x13\x02\x00\x04\xff\xff\xff\x9d",
            19,
            -99,
        ),  # Local temp calibration to -9.9, dp 19
        (
            "_TZE204_cvub6xbb",
            b"\t\x1d\x02\x00\x10\x13\x02\x00\x04\xff\xff\xff\x9d",
            19,
            -99,
        ),  # Local temp calibration to -9.9, dp 19
        (
            "_TZE284_cvub6xbb",
            b"\t\x1d\x02\x00\x10\x13\x02\x00\x04\xff\xff\xff\x9d",
            19,
            -99,
        ),  # Local temp calibration to -9.9, dp 19
    ],
)
async def test_handle_get_data_tmcu(
    zigpy_device_from_v2_quirk, manuf, msg, dp_id, value
):
    """Test handle_get_data for multiple attributes."""

    attr_id = (0xEF << 8) | dp_id

    quirked = zigpy_device_from_v2_quirk(manuf, "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    tmcu_listener = ClusterListener(ep.tuya_manufacturer)

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(tmcu_listener.attribute_updates) == 1
    assert tmcu_listener.attribute_updates[0][0] == attr_id
    assert tmcu_listener.attribute_updates[0][1] == value

    assert ep.tuya_manufacturer.get(attr_id) == value


PILOT_WIRE_DIAGNOSTICS = "tze204-6vwfjkcj-ts0601-0x0000004a.json"

# Reports of a _TZE204_6vwfjkcj pilot wire thermostat
ZCL_PILOT_WIRE_ON = bytes.fromhex("09920200350101000101")  # DP 1: on
ZCL_PILOT_WIRE_POWER = bytes.fromhex("09b902006c0b02000400000ce8")  # DP 11: 330.4 W
ZCL_PILOT_WIRE_TEMPERATURE = bytes.fromhex("097a02003010020004000000d3")  # DP 16
ZCL_PILOT_WIRE_CALIBRATION = bytes.fromhex("099702003a13020004ffffffff")  # DP 19
ZCL_PILOT_WIRE_NO_FAULT = bytes.fromhex("09a802004b1405000100")  # DP 20: bitmap 0
ZCL_PILOT_WIRE_FAULT = bytes.fromhex("09a902004c1405000102")  # DP 20: bitmap 2
ZCL_PILOT_WIRE_VOLTAGE = bytes.fromhex("09bb02006e650200040000091a")  # DP 101
ZCL_PILOT_WIRE_CURRENT = bytes.fromhex("09b802006b660200040000002c")  # DP 102
ZCL_PILOT_WIRE_SIX_MODES = bytes.fromhex("09a60200496a04000101")  # DP 106


def entities_by_attribute(device, platform):
    """Return the entities of a platform by attribute name."""
    return {
        getattr(entity, "_attribute_name", None): entity
        for entity in device.platform_entities.values()
        if platform == entity.PLATFORM
    }


def sent_datapoints(request_mock, cluster):
    """Decode the datapoints sent with set_data on the Tuya cluster."""
    datapoints = []
    for call in request_mock.mock_calls:
        if (
            call.kwargs.get("cluster") != cluster.cluster_id
            or call.kwargs["command_id"] != TuyaMCUCluster.ServerCommandDefs.set_data.id
        ):
            continue
        _, data = foundation.ZCLHeader.deserialize(call.kwargs["data"])
        command = cluster.server_commands[call.kwargs["command_id"]]
        payload, _ = command.schema.deserialize(data)
        datapoints += [
            (dp.dp, dp.data.dp_type, dp.data.raw) for dp in payload.data.datapoints
        ]
    return datapoints


async def test_pilot_wire_reports():
    """Test the reports of the pilot wire thermostat."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, PILOT_WIRE_DIAGNOSTICS, DEVICE_REGISTRY
        )
        ep = device.device.endpoints[1]
        tuya_cluster = ep.tuya_manufacturer

        for message in (
            ZCL_PILOT_WIRE_ON,
            ZCL_PILOT_WIRE_POWER,
            ZCL_PILOT_WIRE_TEMPERATURE,
            ZCL_PILOT_WIRE_CALIBRATION,
            ZCL_PILOT_WIRE_NO_FAULT,
            ZCL_PILOT_WIRE_VOLTAGE,
            ZCL_PILOT_WIRE_CURRENT,
            ZCL_PILOT_WIRE_SIX_MODES,
        ):
            tuya_cluster.handle_message(*tuya_cluster.deserialize(message))
        await gateway.async_block_till_done()

        thermostat = ep.thermostat
        assert thermostat.get("system_mode") == Thermostat.SystemMode.Heat
        assert thermostat.get("local_temperature") == 2110

        sensors = entities_by_attribute(device, Platform.SENSOR)
        assert sensors["power"].native_value == 330.4
        assert sensors["voltage"].native_value == 233.0
        assert sensors["current"].native_value == 0.044
        assert sensors["pilot_wire_type"].native_value == "SixModes"
        numbers = entities_by_attribute(device, Platform.NUMBER)
        assert numbers["local_temperature_calibration"].native_value == -1

        # the fault DP is a bitmap
        fault = entities_by_attribute(device, Platform.BINARY_SENSOR)["fault_alarm"]
        fault_states = [fault.is_on]
        tuya_cluster.handle_message(*tuya_cluster.deserialize(ZCL_PILOT_WIRE_FAULT))
        await gateway.async_block_till_done()
        fault_states.append(fault.is_on)
        assert fault_states == [False, True]

        # no DP reports the heating state
        assert "hvac_action" not in {
            entity.unique_id.rsplit("-", 1)[-1]
            for entity in device.platform_entities.values()
        }


@pytest.mark.parametrize(
    "platform,attribute,value,datapoint",
    [
        (Platform.SELECT, "pilot_wire_mode", "Eco", (2, TuyaDPType.ENUM, b"\x01")),
        (
            Platform.NUMBER,
            "comfort_temperature",
            20.5,
            (118, TuyaDPType.VALUE, b"\x00\x00\x00\xcd"),
        ),
    ],
)
async def test_pilot_wire_commands(platform, attribute, value, datapoint):
    """Test the commands sent to the pilot wire thermostat."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, PILOT_WIRE_DIAGNOSTICS, DEVICE_REGISTRY
        )
        tuya_cluster = device.device.endpoints[1].tuya_manufacturer
        entity = entities_by_attribute(device, platform)[attribute]

        with mock.patch.object(
            tuya_cluster.endpoint, "request", mock.AsyncMock(return_value=[0, 0])
        ) as request:
            if platform == Platform.SELECT:
                await entity.async_select_option(value)
            else:
                await entity.async_set_native_value(value)
            await gateway.async_block_till_done()

        assert sent_datapoints(request, tuya_cluster) == [datapoint]


async def test_pilot_wire_system_mode():
    """Test the system mode of the pilot wire thermostat."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, PILOT_WIRE_DIAGNOSTICS, DEVICE_REGISTRY
        )
        ep = device.device.endpoints[1]
        tuya_cluster = ep.tuya_manufacturer

        with mock.patch.object(
            tuya_cluster.endpoint, "request", mock.AsyncMock(return_value=[0, 0])
        ) as request:
            await ep.thermostat.write_attributes(
                {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
            )
            await gateway.async_block_till_done()

        assert sent_datapoints(request, tuya_cluster) == [(1, TuyaDPType.BOOL, b"\x00")]


async def test_pilot_wire_configure_queries_data():
    """Test the settings are queried on configuration."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, PILOT_WIRE_DIAGNOSTICS, DEVICE_REGISTRY
        )
        tuya_cluster = device.device.endpoints[1].tuya_manufacturer

        with mock.patch.object(
            tuya_cluster.endpoint, "request", mock.AsyncMock(return_value=[0, 0])
        ) as request:
            await device.async_configure()
            await gateway.async_block_till_done()

        assert TUYA_QUERY_DATA in [
            call.kwargs["command_id"]
            for call in request.mock_calls
            if call.kwargs.get("cluster") == tuya_cluster.cluster_id
        ]
