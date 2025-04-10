"""Tests for Sunricher remote device."""

from unittest import mock

import pytest
from zigpy.zcl.foundation import ZCLHeader

import zhaquirks
from zhaquirks.const import BUTTON, COMMAND, PRESS_TYPE
from zhaquirks.sunricher.remote import ZG9002KR12ProRemoteCluster

zhaquirks.setup()


@pytest.mark.parametrize(
    "button_id, press_type_id, expected_action",
    [
        (1, 1, "k1_short_press"),
        (2, 1, "k2_short_press"),
    ],
)
def test_button_press_events(
    zigpy_device_from_v2_quirk, button_id, press_type_id, expected_action
):
    """Test button press events are correctly generated."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Sunricher",
        model="HK-ZRC-K12&RS-E",
    )

    cluster = device.endpoints[1].sunricher_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    button_mask = 1 << (button_id - 1)
    high_byte = (button_mask >> 8) & 0xFF
    low_byte = button_mask & 0xFF

    args = [0x01, high_byte, low_byte, press_type_id]

    cluster.handle_cluster_request(ZCLHeader(), args)

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args[0][0] == expected_action

    event_data = listener.zha_send_event.call_args[0][1]
    press_type_info = cluster.PRESS_TYPES.get(press_type_id)

    assert event_data[BUTTON] == button_id
    assert event_data[PRESS_TYPE] == press_type_info.action
    assert event_data[COMMAND] == "button_press"


def test_multiple_buttons_pressed(zigpy_device_from_v2_quirk):
    """Test multiple buttons pressed at the same time."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Sunricher",
        model="HK-ZRC-K12&RS-E",
    )

    cluster = device.endpoints[1].sunricher_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    button_mask = 3
    high_byte = (button_mask >> 8) & 0xFF
    low_byte = button_mask & 0xFF

    press_type_id = 1
    args = [0x01, high_byte, low_byte, press_type_id]

    cluster.handle_cluster_request(ZCLHeader(), args)

    assert listener.zha_send_event.call_count == 2

    event_names = [call[0][0] for call in listener.zha_send_event.call_args_list]
    assert "k1_short_press" in event_names
    assert "k2_short_press" in event_names


@pytest.mark.parametrize(
    "direction_id, speed, expected_action, expected_direction",
    [
        (1, 10, "clockwise_rotation", "clockwise"),
        (2, 5, "anti_clockwise_rotation", "anti_clockwise"),
    ],
)
def test_knob_rotation_events(
    zigpy_device_from_v2_quirk, direction_id, speed, expected_action, expected_direction
):
    """Test knob rotation events are correctly generated."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Sunricher",
        model="HK-ZRC-K12&RS-E",
    )

    cluster = device.endpoints[1].sunricher_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    args = [0x03, direction_id, 0x00, speed]

    cluster.handle_cluster_request(ZCLHeader(), args)

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args[0][0] == expected_action

    event_data = listener.zha_send_event.call_args[0][1]

    assert event_data[BUTTON] == 9
    assert event_data[PRESS_TYPE] == expected_action
    assert event_data["speed"] == speed


def test_unknown_message_type(zigpy_device_from_v2_quirk):
    """Test handling of unknown message types."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Sunricher",
        model="HK-ZRC-K12&RS-E",
    )

    cluster = device.endpoints[1].sunricher_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    args = [0x99, 0x00, 0x00, 0x00]

    cluster.handle_cluster_request(ZCLHeader(), args)

    assert listener.zha_send_event.call_count == 0


def test_generate_device_automation_triggers():
    """Test generation of device automation triggers."""

    triggers = ZG9002KR12ProRemoteCluster.generate_device_automation_triggers()

    for button in ZG9002KR12ProRemoteCluster.BUTTONS.values():
        for press_type in ZG9002KR12ProRemoteCluster.PRESS_TYPES.values():
            trigger_key = (press_type.trigger, button.trigger)
            assert trigger_key in triggers
            assert (
                triggers[trigger_key][COMMAND] == f"{button.action}_{press_type.action}"
            )

    knob_button = ZG9002KR12ProRemoteCluster.BUTTONS.get(9)
    for direction in ZG9002KR12ProRemoteCluster.KNOB_DIRECTIONS.values():
        trigger_key = (direction.trigger, knob_button.trigger)
        assert trigger_key in triggers
        assert triggers[trigger_key][COMMAND] == direction.action
