"""Tests for Linxura quirks."""

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


zhaquirks.setup()



@pytest.mark.parametrize(
    "quirk",
    (
        zhaquirks.Linxura.button.LinxuraButtonRemote1,
    ),
)
async def test_Linxura_button(zigpy_device_from_quirk, quirk):
    """Test Linxura button remotes."""

    device = zigpy_device_from_quirk(quirk)
    cluster = device.endpoints[1].Linxura_on_off

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