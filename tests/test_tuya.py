"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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
import zhaquirks.tuya.motion
import zhaquirks.tuya.siren

from tests.common import ClusterListener

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"
ZCL_TUYA_SWITCH_ON = b"\tQ\x02\x006\x01\x01\x00\x01\x01"
ZCL_TUYA_SWITCH_OFF = b"\tQ\x02\x006\x01\x01\x00\x01\x00"
ZCL_TUYA_ATTRIBUTE_617_TO_179 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_SIREN_TEMPERATURE = ZCL_TUYA_ATTRIBUTE_617_TO_179
ZCL_TUYA_SIREN_HUMIDITY = b"\tp\x02\x00\x02j\x02\x00\x04\x00\x00\x00U"
ZCL_TUYA_SIREN_ON = b"\t\t\x02\x00\x04h\x01\x00\x01\x01"
ZCL_TUYA_SIREN_OFF = b"\t\t\x02\x00\x04h\x01\x00\x01\x00"


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
    assert len(motion_listener.attribute_updates) == 0
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
