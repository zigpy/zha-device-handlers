"""Tests for konke quirks."""

import asyncio
from unittest import mock

import pytest

from zhaquirks.const import OFF, ON, ZONE_STATE
import zhaquirks.konke.motion

from tests.common import ZCL_IAS_MOTION_COMMAND, ClusterListener


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "quirk", (zhaquirks.konke.motion.KonkeMotion, zhaquirks.konke.motion.KonkeMotionB)
)
async def test_konke_motion(zigpy_device_from_quirk, quirk):
    """Test konke motion sensor."""

    motion_dev = zigpy_device_from_quirk(quirk)

    motion_cluster = motion_dev.endpoints[1].ias_zone
    motion_listener = ClusterListener(motion_cluster)

    occupancy_cluster = motion_dev.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    p1 = mock.patch.object(motion_cluster, "reset_s", 0)
    p2 = mock.patch.object(occupancy_cluster, "reset_s", 0)
    # send motion on IAS zone command
    hdr, args = motion_cluster.deserialize(ZCL_IAS_MOTION_COMMAND)
    with p1, p2:
        motion_cluster.handle_message(hdr, args)

    assert len(motion_listener.cluster_commands) == 1
    assert len(motion_listener.attribute_updates) == 0
    assert motion_listener.cluster_commands[0][1] == ZONE_STATE
    assert motion_listener.cluster_commands[0][2][0] == ON

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == 0x0000
    assert occupancy_listener.attribute_updates[0][1] == 1

    await asyncio.sleep(0.1)

    assert len(motion_listener.cluster_commands) == 2
    assert motion_listener.cluster_commands[1][1] == ZONE_STATE
    assert motion_listener.cluster_commands[1][2][0] == OFF

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 2
    assert occupancy_listener.attribute_updates[1][0] == 0x0000
    assert occupancy_listener.attribute_updates[1][1] == 0
