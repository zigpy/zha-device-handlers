"""Tests for inovelli blue series manufacturer cluster."""

from unittest import mock
from unittest.mock import MagicMock

import zigpy.types as t
from zigpy.zcl import ClusterType

import zhaquirks

zhaquirks.setup()


def test_mfg_cluster_events(zigpy_device_from_v2_quirk):
    """Test Inovelli manufacturer cluster generates correct events."""
    data = b"\x15/\x12\x05\x00\x03\x00"  # button_3_press event
    cluster_id = 0xFC31
    endpoint_id = 2

    class Listener:
        zha_send_event = mock.MagicMock()

    device = zigpy_device_from_v2_quirk(
        "Inovelli", "VZM31-SN", cluster_ids={2: {0xFC31: ClusterType.Client}}
    )
    device._packet_debouncer.filter = MagicMock(return_value=False)
    cluster_listener = Listener()
    device.endpoints[endpoint_id].out_clusters[cluster_id].add_listener(
        cluster_listener
    )

    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(data),
        )
    )

    assert cluster_listener.zha_send_event.call_count == 1
    assert cluster_listener.zha_send_event.call_args == mock.call(
        "button_3_press", {"button": "button_3", "press_type": "press", "command_id": 0}
    )

    cluster_listener.zha_send_event.reset_mock()

    led_effect_complete_data = b"\x15/\x12\x0c$\x10"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(led_effect_complete_data),
        )
    )

    assert cluster_listener.zha_send_event.call_count == 1
    assert cluster_listener.zha_send_event.call_args == mock.call(
        "led_effect_complete_ALL_LEDS",
        {"notification_type": "ALL_LEDS", "command_id": 36},
    )
