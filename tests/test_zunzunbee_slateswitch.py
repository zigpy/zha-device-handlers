"""Tests for ZunZunBee quirks."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

import zhaquirks

zhaquirks.setup()


async def test_button_ias(zigpy_device_from_v2_quirk):
    """Test ZunZunBee button remotes."""
    device = zigpy_device_from_v2_quirk("zunzunbee", "SSWZ8T")
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    # Define button press values (hex + long press variants)
    button_values = [
        0x2,
        0x3,
        0x4,
        0x5,
        0x8,
        0x9,
        0x10,
        0x11,
        0x20,
        0x21,
        0x40,
        0x41,
        0x80,
        0x81,
        0x100,
        0x101,
    ]

    for value in button_values:
        cluster.update_attribute(ias_zone_status_attr_id, value)
        assert listener.attribute_updated.call_args[0][0] == ias_zone_status_attr_id
        assert listener.attribute_updated.call_args[0][1] == value

    assert listener.attribute_updated.call_count == len(button_values)
    assert listener.zha_send_event.call_count == len(button_values)


@pytest.mark.parametrize(
    "message, button, press_type",
    [
        (
            b"\x18\n\n\x02\x00\x19\x02\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x03\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x04\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x05\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x08\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x09\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x10\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x11\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x20\x00\xfe\xff0\x01",
            "button_5",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x21\x00\xfe\xff0\x01",
            "button_5",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x40\x00\xfe\xff0\x01",
            "button_6",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x41\x00\xfe\xff0\x01",
            "button_6",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x80\x00\xfe\xff0\x01",
            "button_7",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x81\x00\xfe\xff0\x01",
            "button_7",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x00\x01\xfe\xff0\x01",
            "button_8",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x01\x01\xfe\xff0\x01",
            "button_8",
            "remote_button_long_press",
        ),
    ],
)
async def test_button_triggers(zigpy_device_from_v2_quirk, message, button, press_type):
    """Test ZHA_SEND_EVENT case."""
    device = zigpy_device_from_v2_quirk("zunzunbee", "SSWZ8T")
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(message),
        )
    )

    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args == mock.call(
        f"{button}_{press_type}",
        {"button": button, "press_type": press_type},
    )


async def test_discard_invalid_value(zigpy_device_from_v2_quirk):
    """Test that invalid values are discarded without triggering events."""
    device = zigpy_device_from_v2_quirk("zunzunbee", "SSWZ8T")
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id
    invalid_value = 6  # example invalid value
    cluster.update_attribute(ias_zone_status_attr_id, invalid_value)

    assert listener.attribute_updated.call_args[0][0] == ias_zone_status_attr_id
    assert listener.attribute_updated.call_args[0][1] == invalid_value

    listener.zha_send_event.assert_not_called()
