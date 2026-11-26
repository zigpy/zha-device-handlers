"""Tests for Tuya Thermostat."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya import TUYA_MCU_VERSION_RSP, TUYA_QUERY_DATA, TuyaDPType
from zhaquirks.tuya.mcu import TuyaClusterData, TuyaMCUCluster
from zhaquirks.tuya.ts0601_zxkwaztm import TuyaThermostatSchedule

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
        (
            "_TZE204_zxkwaztm",
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
        (
            "_TZE204_zxkwaztm",
            b"\t\x1d\x02\x00\x10\x6d\x02\x00\x04\xff\xff\xff\x9d",
            109,
            -99,
        ),  # Local temp calibration to -9.9, dp 109
        (
            "_TZE204_zxkwaztm",
            b"\t\x1d\x02\x00\x10\x02\x02\x00\x04\x00\x00\x00\x01",
            2,
            1,
        ),  # Preset Mode to 1, dp 2
        (
            "_TZE204_zxkwaztm",
            b"\t\x1d\x02\x00\x10\x1f\x02\x00\x04\x00\x00\x00\x02",
            31,
            2,
        ),  # Working Day to 2, dp 31
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


async def test_zxkwaztm_schedule_dp_round_trip(zigpy_device_from_v2_quirk):
    """Test decoding and writing six weekday and two weekend schedule slots."""
    schedule = bytes.fromhex(
        "063700af093700eb0c3700eb113700af133700af163700af0a0000f0150000b4"
    )
    quirked = zigpy_device_from_v2_quirk("_TZE204_zxkwaztm", "TS0601")
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    thermostat = ep.thermostat

    assert tuya_cluster is not None
    assert thermostat is not None
    hdr, data = tuya_cluster.deserialize(
        b"\x09\x01\x02\x00\x02\x43\x00\x00\x20" + schedule
    )
    assert hdr.command_id == 2
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS

    expected_slots = [
        (6, 55, 175),
        (9, 55, 235),
        (12, 55, 235),
        (17, 55, 175),
        (19, 55, 175),
        (22, 55, 175),
    ]
    for slot, (hour, minute, temperature) in enumerate(expected_slots, start=1):
        assert thermostat.get(f"schedule_slot_{slot}_hour") == hour
        assert thermostat.get(f"schedule_slot_{slot}_minute") == minute
        assert thermostat.get(f"schedule_slot_{slot}_temperature") == temperature

    expected_weekend_slots = [(10, 0, 240), (21, 0, 180)]
    for slot, (hour, minute, temperature) in enumerate(expected_weekend_slots, start=1):
        assert thermostat.get(f"weekend_schedule_slot_{slot}_hour") == hour
        assert thermostat.get(f"weekend_schedule_slot_{slot}_minute") == minute
        assert (
            thermostat.get(f"weekend_schedule_slot_{slot}_temperature") == temperature
        )

    result = tuya_cluster.from_cluster_data(
        TuyaClusterData(
            endpoint_id=1,
            cluster_name=TuyaThermostatSchedule.ep_attribute,
            cluster_attr="schedule_slot_1_temperature",
            attr_value=180,
        )
    )
    datapoint = result[0].datapoints[0]
    assert datapoint.dp == 67
    assert datapoint.data.dp_type == TuyaDPType.RAW
    assert bytes(datapoint.data.raw) == schedule[:2] + b"\x00\xb4" + schedule[4:]

    result = tuya_cluster.from_cluster_data(
        TuyaClusterData(
            endpoint_id=1,
            cluster_name=TuyaThermostatSchedule.ep_attribute,
            cluster_attr="weekend_schedule_slot_2_temperature",
            attr_value=190,
        )
    )
    datapoint = result[0].datapoints[0]
    assert datapoint.dp == 67
    assert datapoint.data.dp_type == TuyaDPType.RAW
    assert bytes(datapoint.data.raw) == schedule[:-2] + b"\x00\xbe"


async def test_zxkwaztm_queries_data_on_configuration(zigpy_device_from_v2_quirk):
    """Test that the thermostat is queried for its current datapoints."""
    quirked = zigpy_device_from_v2_quirk("_TZE204_zxkwaztm", "TS0601")

    with mock.patch(
        "zigpy.zcl.Cluster.request",
        mock.AsyncMock(return_value=(foundation.Status.SUCCESS, "done")),
    ) as request_mock:
        await quirked.apply_custom_configuration()

    query_calls = [
        call for call in request_mock.mock_calls if call.args[1] == TUYA_QUERY_DATA
    ]
    assert len(query_calls) == 1
