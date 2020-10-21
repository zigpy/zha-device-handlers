"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest
from zigpy.zcl import foundation

from zhaquirks.const import OFF, ON, ZONE_STATE
import zhaquirks.tuya.motion

from tests.common import ClusterListener

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"
ZCL_TUYA_SWITCH_ON = b"\tQ\x02\x006\x01\x01\x00\x01\x01"
ZCL_TUYA_SWITCH_OFF = b"\tQ\x02\x006\x01\x01\x00\x01\x00"


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
