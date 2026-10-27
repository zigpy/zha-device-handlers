"""Tests for ZunZunBee quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.security import IasZone

from tests.common import ButtonEventRecorder, ClusterListener, send_command
import zhaquirks

zhaquirks.setup()


async def test_button_ias(zigpy_device_from_v2_quirk):
    """Test ZunZunBee button remotes."""
    device = zigpy_device_from_v2_quirk("zunzunbee", "SSWZ8T")
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id
    cluster = device.endpoints[1].ias_zone
    cluster_listener = ClusterListener(cluster)
    zha_listener = mock.MagicMock()
    cluster.add_listener(zha_listener)

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

    for i, value in enumerate(button_values):
        cluster.update_attribute(ias_zone_status_attr_id, value)
        assert cluster_listener.attribute_updates[i] == (ias_zone_status_attr_id, value)

    assert len(cluster_listener.attribute_updates) == len(button_values)
    assert zha_listener.zha_send_event.call_count == len(button_values)


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
    cluster_listener = ClusterListener(cluster)
    zha_listener = mock.MagicMock()
    cluster.add_listener(zha_listener)

    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id
    invalid_value = 6  # example invalid value
    cluster.update_attribute(ias_zone_status_attr_id, invalid_value)

    assert cluster_listener.attribute_updates[0] == (
        ias_zone_status_attr_id,
        invalid_value,
    )

    assert len(zha_listener.zha_send_event.mock_calls) == 0


async def test_button_events(zigpy_device_from_v2_quirk):
    """Test the button event entities of the Slate Switch."""
    device = zigpy_device_from_v2_quirk("zunzunbee", "SSWZ8T")
    device.endpoints[1].profile_id = zha.PROFILE_ID
    device.endpoints[1].device_type = zha.DeviceType.IAS_ZONE

    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {
        f"button_{number}": ["press_end", "long_press_start"] for number in range(1, 9)
    }
    assert recorder.entities["button_8"].translation_placeholders == {
        "button_number": "8"
    }

    tsn = 0
    for number in range(1, 9):
        # short press, long press, invalid button, as zone status change
        # notifications
        for zone_status in (1 << number, 1 << number | 1, 6):
            tsn += 1
            send_command(
                device,
                1,
                IasZone.cluster_id,
                "status_change_notification",
                zone_status,
                0,
                0,
                0,
                cluster_type=ClusterType.Server,
                tsn=tsn,
            )

    expected = [
        (f"button_{number}", event_type)
        for number in range(1, 9)
        for event_type in ("press_end", "long_press_start")
    ]
    assert recorder.pop() == expected

    for number in range(1, 9):
        # the same as zone status attribute reports
        for zone_status in (1 << number, 1 << number | 1, 6):
            tsn += 1
            device.packet_received(
                t.ZigbeePacket(
                    profile_id=zha.PROFILE_ID,
                    cluster_id=IasZone.cluster_id,
                    src_ep=1,
                    dst_ep=1,
                    tsn=tsn,
                    data=t.SerializableBytes(
                        b"\x18"
                        + bytes([tsn])
                        + b"\x0a\x02\x00\x19"
                        + t.bitmap16(zone_status).serialize()
                    ),
                )
            )

    assert recorder.pop() == expected
