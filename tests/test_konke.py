"""Tests for konke quirks."""

import asyncio
from unittest import mock

import pytest

from tests.common import ZCL_IAS_MOTION_COMMAND, ClusterListener
import zhaquirks
from zhaquirks.const import (
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_SINGLE,
    OFF,
    ON,
    PRESS_TYPE,
    ZONE_STATUS_CHANGE_COMMAND,
)
import zhaquirks.konke.motion

zhaquirks.setup()


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
    assert motion_listener.cluster_commands[0][1] == ZONE_STATUS_CHANGE_COMMAND
    assert motion_listener.cluster_commands[0][2][0] == ON

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0][0] == 0x0000
    assert occupancy_listener.attribute_updates[0][1] == 1

    await asyncio.sleep(0.1)

    assert len(motion_listener.cluster_commands) == 2
    assert motion_listener.cluster_commands[1][1] == ZONE_STATUS_CHANGE_COMMAND
    assert motion_listener.cluster_commands[1][2][0] == OFF

    assert len(occupancy_listener.cluster_commands) == 0
    assert len(occupancy_listener.attribute_updates) == 2
    assert occupancy_listener.attribute_updates[1][0] == 0x0000
    assert occupancy_listener.attribute_updates[1][1] == 0


@pytest.mark.parametrize(
    "quirk",
    (
        zhaquirks.konke.button.KonkeButtonRemote1,
        zhaquirks.konke.button.KonkeButtonRemote2,
    ),
)
async def test_konke_button(zigpy_device_from_quirk, quirk):
    """Test Konke button remotes."""

    device = zigpy_device_from_quirk(quirk)
    cluster = device.endpoints[1].konke_on_off

    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # single press
    message = b"\x08W\n\x00\x00\x10\x80"
    device.handle_message(260, cluster.cluster_id, 1, 1, message)
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0][0][0] == COMMAND_SINGLE
    assert listener.zha_send_event.call_args_list[0][0][1][PRESS_TYPE] == COMMAND_SINGLE
    assert listener.zha_send_event.call_args_list[0][0][1][COMMAND_ID] == 0x80

    # double press
    listener.reset_mock()
    message = b"\x08X\n\x00\x00\x10\x81"
    device.handle_message(260, cluster.cluster_id, 1, 1, message)
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0][0][0] == COMMAND_DOUBLE
    assert listener.zha_send_event.call_args_list[0][0][1][PRESS_TYPE] == COMMAND_DOUBLE
    assert listener.zha_send_event.call_args_list[0][0][1][COMMAND_ID] == 0x81

    # long press
    listener.reset_mock()
    message = b"\x08Y\n\x00\x00\x10\x82"
    device.handle_message(260, cluster.cluster_id, 1, 1, message)
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args_list[0][0][0] == COMMAND_HOLD
    assert listener.zha_send_event.call_args_list[0][0][1][PRESS_TYPE] == COMMAND_HOLD
    assert listener.zha_send_event.call_args_list[0][0][1][COMMAND_ID] == 0x82
