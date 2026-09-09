"""Tests for Namron quirks."""

from unittest import mock

import pytest
import zigpy.types as t

import zhaquirks
from zhaquirks.namron.remote_4512793 import NamronPrivateRemoteCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "payload, event_name, event_args",
    [
        (
            b"\x01\x01",
            "button_1_remote_button_short_press",
            {"button": "button_1", "press_type": "remote_button_short_press"},
        ),
        (
            b"\x01\x02",
            "button_1_remote_button_long_press",
            {"button": "button_1", "press_type": "remote_button_long_press"},
        ),
        (
            b"\x01\x04",
            "button_1_remote_button_long_release",
            {"button": "button_1", "press_type": "remote_button_long_release"},
        ),
        (
            b"\x06\x01",
            "button_6_remote_button_short_press",
            {"button": "button_6", "press_type": "remote_button_short_press"},
        ),
        (
            b"\x03\x02",
            "button_3_remote_button_long_press",
            {"button": "button_3", "press_type": "remote_button_long_press"},
        ),
    ],
)
async def test_button_triggers(
    zigpy_device_from_v2_quirk, payload, event_name, event_args
):
    """Test that real captured button/action payloads produce the right zha_event."""
    device = zigpy_device_from_v2_quirk("Namron AS", "4512793")
    cluster = device.endpoints[1].namron_private_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Real captured frame header: frame_control=0x19, tsn=<any>, command_id=0x00
    header = b"\x19" + bytes([0x42]) + b"\x00"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=NamronPrivateRemoteCluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(header + payload),
        )
    )

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args == mock.call(event_name, event_args)


async def test_unknown_button_and_action_discarded(zigpy_device_from_v2_quirk):
    """Unrecognized button/action values should not raise or emit an event."""
    device = zigpy_device_from_v2_quirk("Namron AS", "4512793")
    cluster = device.endpoints[1].namron_private_remote
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    header = b"\x19" + bytes([0x42]) + b"\x00"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=NamronPrivateRemoteCluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(header + b"\x09\x09"),
        )
    )

    assert listener.zha_send_event.call_count == 0
