"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, get_device
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATE,
)
from zhaquirks.tuya import Data, TuyaManufClusterAttributes
import zhaquirks.tuya.electric_heating
import zhaquirks.tuya.motion
import zhaquirks.tuya.siren
import zhaquirks.tuya.ts0042
import zhaquirks.tuya.valve

from tests.common import ClusterListener

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"
ZCL_TUYA_SWITCH_ON = b"\tQ\x02\x006\x01\x01\x00\x01\x01"
ZCL_TUYA_SWITCH_OFF = b"\tQ\x02\x006\x01\x01\x00\x01\x00"
ZCL_TUYA_ATTRIBUTE_617_TO_179 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_SIREN_TEMPERATURE = ZCL_TUYA_ATTRIBUTE_617_TO_179
ZCL_TUYA_SIREN_HUMIDITY = b"\tp\x02\x00\x02j\x02\x00\x04\x00\x00\x00U"
ZCL_TUYA_SIREN_ON = b"\t\t\x02\x00\x04h\x01\x00\x01\x01"
ZCL_TUYA_SIREN_OFF = b"\t\t\x02\x00\x04h\x01\x00\x01\x00"
ZCL_TUYA_VALVE_TEMPERATURE = b"\tp\x02\x00\x02\x03\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_VALVE_TARGET_TEMP = b"\t3\x01\x03\x05\x02\x02\x00\x04\x00\x00\x002"
ZCL_TUYA_VALVE_OFF = b"\t2\x01\x03\x04\x04\x04\x00\x01\x00"
ZCL_TUYA_VALVE_SCHEDULE = b"\t2\x01\x03\x04\x04\x04\x00\x01\x01"
ZCL_TUYA_VALVE_MANUAL = b"\t2\x01\x03\x04\x04\x04\x00\x01\x02"
ZCL_TUYA_EHEAT_TEMPERATURE = b"\tp\x02\x00\x02\x18\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_EHEAT_TARGET_TEMP = b"\t3\x01\x03\x05\x10\x02\x00\x04\x00\x00\x00\x15"


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.motion.TuyaMotion,))
async def test_motion(zigpy_device_from_quirk, quirk):
    """Test tuya motion sensor."""

    motion_dev = zigpy_device_from_quirk(quirk)

    motion_cluster = motion_dev.endpoints[1].ias_zone
    motion_listener = ClusterListener(motion_cluster)

    tuya_cluster = motion_dev.endpoints[1].tuya_manufacturer

    # send motion on Tuya manufacturer specific cluster
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_MOTION)
    with mock.patch.object(motion_cluster, "reset_s", 0):
        tuya_cluster.handle_message(hdr, args)

    assert len(motion_listener.cluster_commands) == 1
    assert len(motion_listener.attribute_updates) == 1
    assert motion_listener.cluster_commands[0][1] == ZONE_STATE
    assert motion_listener.cluster_commands[0][2][0] == ON

    await asyncio.gather(asyncio.sleep(0), asyncio.sleep(0), asyncio.sleep(0))

    assert len(motion_listener.cluster_commands) == 2
    assert motion_listener.cluster_commands[1][1] == ZONE_STATE
    assert motion_listener.cluster_commands[1][2][0] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.singleswitch.TuyaSingleSwitch,))
async def test_singleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya single switch."""

    switch_dev = zigpy_device_from_quirk(quirk)

    switch_cluster = switch_dev.endpoints[1].on_off
    switch_listener = ClusterListener(switch_cluster)

    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_ON)
    tuya_cluster.handle_message(hdr, args)
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_OFF)
    tuya_cluster.handle_message(hdr, args)

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.singleswitch.TuyaSingleSwitch,))
async def test_singleswitch_requests(zigpy_device_from_quirk, quirk):
    """Test tuya single switch."""

    switch_dev = zigpy_device_from_quirk(quirk)

    switch_cluster = switch_dev.endpoints[1].on_off
    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:

        status = switch_cluster.command(0x0000)
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x00\x01\x01\x00\x01\x00",
            expect_reply=True,
            command_id=0,
        )
        assert status == 0

        status = switch_cluster.command(0x0001)
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x00\x01\x01\x00\x01\x01",
            expect_reply=True,
            command_id=0,
        )
        assert status == 0

    status = switch_cluster.command(0x0002)
    assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


async def test_tuya_data_conversion():
    """Test tuya conversion from Data to ztype and reverse."""
    assert Data([4, 0, 0, 1, 39]).to_value(t.uint32_t) == 295
    assert Data([4, 0, 0, 0, 220]).to_value(t.uint32_t) == 220
    assert Data([4, 255, 255, 255, 236]).to_value(t.int32s) == -20
    assert Data.from_value(t.uint32_t(295)) == [4, 0, 0, 1, 39]
    assert Data.from_value(t.uint32_t(220)) == [4, 0, 0, 0, 220]
    assert Data.from_value(t.int32s(-20)) == [4, 255, 255, 255, 236]


class TestManufCluster(TuyaManufClusterAttributes):
    """Cluster for synthetic tests."""

    manufacturer_attributes = {617: ("test_attribute", t.uint32_t)}


class TestDevice(CustomDevice):
    """Device for synthetic tests."""

    signature = {
        MODELS_INFO: [("_test_manuf", "_test_device")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [TestManufCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [TestManufCluster],
                OUTPUT_CLUSTERS: [],
            }
        },
    }


@pytest.mark.parametrize("quirk", (TestDevice,))
async def test_tuya_receive_attribute(zigpy_device_from_quirk, quirk):
    """Test conversion of tuya commands to attributes."""

    test_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = test_dev.endpoints[1].tuya_manufacturer
    listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_ATTRIBUTE_617_TO_179)
    tuya_cluster.handle_message(hdr, args)

    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][0] == 617
    assert listener.attribute_updates[0][1] == 179


@pytest.mark.parametrize("quirk", (TestDevice,))
async def test_tuya_send_attribute(zigpy_device_from_quirk, quirk):
    """Test conversion of attributes to tuya commands."""

    test_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = test_dev.endpoints[1].tuya_manufacturer

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        status = await tuya_cluster.write_attributes({617: 179})
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01i\x02\x00\x04\x00\x00\x00\xb3",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.siren.TuyaSiren,))
async def test_siren_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya siren standard state reporting from incoming commands."""

    siren_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = siren_dev.endpoints[1].tuya_manufacturer

    temp_listener = ClusterListener(siren_dev.endpoints[1].temperature)
    humid_listener = ClusterListener(siren_dev.endpoints[1].humidity)
    switch_listener = ClusterListener(siren_dev.endpoints[1].on_off)

    frames = (
        ZCL_TUYA_SIREN_TEMPERATURE,
        ZCL_TUYA_SIREN_HUMIDITY,
        ZCL_TUYA_SIREN_ON,
        ZCL_TUYA_SIREN_OFF,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(temp_listener.cluster_commands) == 0
    assert len(temp_listener.attribute_updates) == 1
    assert temp_listener.attribute_updates[0][0] == 0x0000
    assert temp_listener.attribute_updates[0][1] == 1790

    assert len(humid_listener.cluster_commands) == 0
    assert len(humid_listener.attribute_updates) == 1
    assert humid_listener.attribute_updates[0][0] == 0x0000
    assert humid_listener.attribute_updates[0][1] == 8500

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.siren.TuyaSiren,))
async def test_siren_send_attribute(zigpy_device_from_quirk, quirk):
    """Test tuya siren outgoing commands."""

    siren_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = siren_dev.endpoints[1].tuya_manufacturer
    switch_cluster = siren_dev.endpoints[1].on_off

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        status = await switch_cluster.command(0x0000)
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01h\x01\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await switch_cluster.command(0x0001)
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02h\x01\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = switch_cluster.command(0x0003)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.valve.SiterwellGS361,))
async def test_valve_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)

    frames = (
        ZCL_TUYA_VALVE_TEMPERATURE,
        ZCL_TUYA_VALVE_TARGET_TEMP,
        ZCL_TUYA_VALVE_OFF,
        ZCL_TUYA_VALVE_SCHEDULE,
        ZCL_TUYA_VALVE_MANUAL,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 13
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 500
    assert thermostat_listener.attribute_updates[2][0] == 0x001C  # OFF
    assert thermostat_listener.attribute_updates[2][1] == 0x00
    assert thermostat_listener.attribute_updates[3][0] == 0x001E
    assert thermostat_listener.attribute_updates[3][1] == 0x00
    assert thermostat_listener.attribute_updates[4][0] == 0x0029
    assert thermostat_listener.attribute_updates[4][1] == 0x00
    assert thermostat_listener.attribute_updates[5][0] == 0x001C  # SCHEDULE
    assert thermostat_listener.attribute_updates[5][1] == 0x04
    assert thermostat_listener.attribute_updates[6][0] == 0x0025
    assert thermostat_listener.attribute_updates[6][1] == 0x01
    assert thermostat_listener.attribute_updates[7][0] == 0x001E
    assert thermostat_listener.attribute_updates[7][1] == 0x04
    assert thermostat_listener.attribute_updates[8][0] == 0x0029
    assert thermostat_listener.attribute_updates[8][1] == 0x01
    assert thermostat_listener.attribute_updates[9][0] == 0x001C  # MANUAL
    assert thermostat_listener.attribute_updates[9][1] == 0x04
    assert thermostat_listener.attribute_updates[10][0] == 0x0025
    assert thermostat_listener.attribute_updates[10][1] == 0x00
    assert thermostat_listener.attribute_updates[11][0] == 0x001E
    assert thermostat_listener.attribute_updates[11][1] == 0x04
    assert thermostat_listener.attribute_updates[12][0] == 0x0029
    assert thermostat_listener.attribute_updates[12][1] == 0x01


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.valve.SiterwellGS361,))
async def test_valve_send_attribute(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        status = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\xfa",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02\x04\x04\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x04,
            }
        )
        m1.assert_called_with(
            61184,
            3,
            b"\x01\x03\x00\x00\x03\x04\x04\x00\x01\x02",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x01,
            }
        )
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x04\x04\x04\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VALVE_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            61184,
            5,
            b"\x01\x05\x00\x00\x05\x02\x02\x00\x04\x00\x00\x00F",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.electric_heating.MoesBHT,))
async def test_eheating_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    electric_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = electric_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(electric_dev.endpoints[1].thermostat)

    frames = (ZCL_TUYA_EHEAT_TEMPERATURE, ZCL_TUYA_EHEAT_TARGET_TEMP)
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 2
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 2100


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.electric_heating.MoesBHT,))
async def test_eheat_send_attribute(zigpy_device_from_quirk, quirk):
    """Test electric thermostat outgoing commands."""

    eheat_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = eheat_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = eheat_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        status = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x10\x02\x00\x04\x00\x00\x00\x19",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02\x01\x01\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x04,
            }
        )
        m1.assert_called_with(
            61184,
            3,
            b"\x01\x03\x00\x00\x03\x01\x01\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_EHEAT_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x04\x10\x02\x00\x04\x00\x00\x00\x17",
            expect_reply=False,
            command_id=0,
        )
        assert status == (foundation.Status.SUCCESS,)

        status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize(
    "quirk, manufacturer",
    (
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042, "_TZ3000_owgcnkrh"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042, "_TZ3400_keyjhapk"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042, "_some_random_manuf"),
        (zhaquirks.tuya.ts0042.BenexmartRemote0042, "_TZ3000_adkvzooy"),
        (zhaquirks.tuya.ts0042.BenexmartRemote0042, "_TZ3400_keyjhapk"),
        (zhaquirks.tuya.ts0042.BenexmartRemote0042, "another random manufacturer"),
    ),
)
async def test_tuya_wildcard_manufacturer(zigpy_device_from_quirk, quirk, manufacturer):
    """Test thermostatic valve outgoing commands."""

    zigpy_dev = zigpy_device_from_quirk(quirk, apply_quirk=False)
    zigpy_dev.manufacturer = manufacturer

    quirked_dev = get_device(zigpy_dev)
    assert isinstance(quirked_dev, quirk)
