"""Tests for Tuya Thermostat."""

from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya import (
    TUYA_MCU_VERSION_RSP,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
    TuyaNewManufCluster,
)
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


def _tuya_frame(dp: int, dp_type: TuyaDPType, raw: bytes, tsn: int = 2) -> bytes:
    """Build a 0xEF00 ``set_data_response`` (DP report) Zigbee frame.

    Layout: ZCL header (frame_control, tsn, command_id=0x02) followed by the
    serialized ``TuyaCommand``.
    """
    command = TuyaCommand()
    command.status = t.uint8_t(0)
    command.tsn = t.uint8_t(tsn)

    data = TuyaData()
    data.dp_type = dp_type
    data.function = t.uint8_t(0)
    data.raw = raw

    datapoint = TuyaDatapointData()
    datapoint.dp = dp
    datapoint.data = data
    command.datapoints = [datapoint]

    return b"\x09" + bytes([tsn]) + b"\x02" + command.serialize()


@pytest.mark.parametrize(
    ("frame", "ep_attr", "attribute", "expected"),
    [
        # DP 16 current temperature: 235 -> 2350 (23.5 degC, *10)
        (
            _tuya_frame(16, TuyaDPType.VALUE, b"\x00\x00\x00\xeb"),
            "temperature",
            "measured_value",
            2350,
        ),
        # DP 50 target temperature: 220 -> 220 (22.0 degC)
        (
            _tuya_frame(50, TuyaDPType.VALUE, b"\x00\x00\x00\xdc"),
            TuyaMCUCluster.ep_attribute,
            "temp_set",
            220,
        ),
        # DP 47 valve state: 1 -> open
        (
            _tuya_frame(47, TuyaDPType.ENUM, b"\x01"),
            TuyaMCUCluster.ep_attribute,
            "valve_state",
            1,
        ),
        # DP 109 floor temperature: 300 -> 300 (30.0 degC, divisor 10)
        (
            _tuya_frame(109, TuyaDPType.VALUE, b"\x00\x00\x01\x2c"),
            TuyaMCUCluster.ep_attribute,
            "floor_temp",
            300,
        ),
        # DP 39 child lock: 1 -> on
        (
            _tuya_frame(39, TuyaDPType.BOOL, b"\x01"),
            TuyaMCUCluster.ep_attribute,
            "child_lock",
            1,
        ),
        # DP 101 temperature calibration: -20 -> -2.0 degC (int32 big endian)
        (
            _tuya_frame(101, TuyaDPType.VALUE, b"\xff\xff\xff\xec"),
            TuyaMCUCluster.ep_attribute,
            "temp_calibration",
            -20,
        ),
        # DP 2 work mode: 1 -> temporary manual
        (
            _tuya_frame(2, TuyaDPType.ENUM, b"\x01"),
            TuyaMCUCluster.ep_attribute,
            "work_mode",
            1,
        ),
        # DP 115 RGB ambient light: 1 -> on
        (
            _tuya_frame(115, TuyaDPType.BOOL, b"\x01"),
            TuyaMCUCluster.ep_attribute,
            "rgb_light",
            1,
        ),
    ],
)
async def test_zhtsr_thermostat_reports(
    zigpy_device_from_v2_quirk, frame, ep_attr, attribute, expected
):
    """Test the ZHT-SR / BHT-009 thermostat quirk attribute reporting."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    device._packet_debouncer.filter = mock.MagicMock(return_value=False)

    cluster = device.endpoints[1].in_clusters[TuyaNewManufCluster.cluster_id]

    with mock.patch.object(cluster, "send_default_rsp"):
        device.packet_received(
            t.ZigbeePacket(
                profile_id=zha.PROFILE_ID,
                src_ep=1,
                cluster_id=TuyaNewManufCluster.cluster_id,
                data=t.SerializableBytes(frame),
            )
        )

    cluster = getattr(device.endpoints[1], ep_attr)
    attrs = await cluster.read_attributes(attributes=[attribute])

    assert attrs[0].get(attribute) == expected


async def test_zhtsr_thermostat_device_type(zigpy_device_from_v2_quirk):
    """Test the quirk forces the endpoint device type to a thermostat.

    The device reports device_type 0x0051 (Smart Plug), which makes Home
    Assistant create no climate entity. The quirk must replace it.
    """
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")

    assert device.endpoints[1].device_type == zha.DeviceType.THERMOSTAT


async def test_zhtsr_thermostat_clusters_present(zigpy_device_from_v2_quirk):
    """Test the expected clusters are created on endpoint 1."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    ep = device.endpoints[1]

    assert OnOff.cluster_id in ep.in_clusters
    assert Thermostat.cluster_id in ep.in_clusters
    assert TuyaNewManufCluster.cluster_id in ep.in_clusters
    assert ep.temperature is not None


async def test_zhtsr_thermostat_target_temperature_write(
    zigpy_device_from_v2_quirk,
):
    """Test writing the target temperature emits DP 50 with the right value."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(cluster, "request") as request_mock:
        await cluster.write_attributes({"temp_set": 225})

    assert request_mock.call_count == 1
    command = request_mock.call_args[0][3]
    assert len(command.datapoints) == 1
    datapoint = command.datapoints[0]
    assert datapoint.dp == 50
    assert datapoint.data.raw == b"\x00\x00\x00\xe1"  # 225 -> 22.5 degC


@pytest.mark.parametrize(
    ("attribute", "value", "dp", "raw"),
    [
        ("child_lock", 1, 39, b"\x01"),
        ("work_mode", 1, 2, b"\x01"),
        ("backlight", 60, 48, b"\x00\x00\x00\x3c"),
    ],
)
async def test_zhtsr_thermostat_other_writes(
    zigpy_device_from_v2_quirk, attribute, value, dp, raw
):
    """Test writing other configuration attributes emits the right DP."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(cluster, "request") as request_mock:
        await cluster.write_attributes({attribute: value})

    assert request_mock.call_count == 1
    command = request_mock.call_args[0][3]
    datapoint = command.datapoints[0]
    assert datapoint.dp == dp
    assert datapoint.data.raw == raw
