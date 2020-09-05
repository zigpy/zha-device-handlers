"""Tests for Tuya quirks."""

import asyncio
from unittest import mock

import pytest

from zhaquirks.const import OFF, ON, ZONE_STATE
import zhaquirks.tuya.motion

from tests.common import ClusterListener

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"


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
