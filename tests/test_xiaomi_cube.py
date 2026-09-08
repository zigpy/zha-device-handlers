"""Tests for Xiaomi Aqara Cube AQGL01."""

from unittest.mock import MagicMock

import pytest
from zigpy.types import AddrMode, AddrModeAddress, SerializableBytes, ZigbeePacket

import zhaquirks
from zhaquirks.xiaomi.aqara.cube_aqgl01 import CubeAQGL01

zhaquirks.setup()


@pytest.fixture
def cube_device(zigpy_device_from_quirk):
    """Create a cube device for testing."""
    return zigpy_device_from_quirk(CubeAQGL01)


# fmt: off
test_cases = [
    # Some events I grabbed from the logs:
    # Gesture mode:
    (2, 18, b"\x18\x36\x0a\x55\x00\x21\x00\x00", "shake", {"value": 0}),
    (2, 18, b"\x18\x49\x0a\x55\x00\x21\x6b\x00", "flip", {"value": 107, "flip_degrees": 90, "deactivated_face": 6, "activated_face": 4}),
    (2, 18, b"\x18\x49\x0a\x55\x00\x21\x6c\x00", "flip", {"value": 108, "flip_degrees": 90, "deactivated_face": 6, "activated_face": 5}),
    (2, 18, b"\x18\x49\x0a\x55\x00\x21\x65\x00", "flip", {"value": 101, "flip_degrees": 90, "deactivated_face": 5, "activated_face": 6}),
    (2, 18, b"\x18\x49\x0a\x55\x00\x21\x41\x00", "flip", {"value": 65, "flip_degrees": 90, "deactivated_face": 1, "activated_face": 2}),
    (2, 18, b"\x18\x49\x0a\x55\x00\x21\x80\x00", "flip", {"value": 128, "flip_degrees": 180, "deactivated_face": 6, "activated_face": 1}),
    (2, 18, b"\x18\x4b\x0a\x55\x00\x21\x03\x01", "slide", {"value": 259, "activated_face": 4}),
    (3, 12, b"\x18\x50\x0a\x0b\x01\x21\xf4\x01\x55\x00\x39\xff\xff\x8c\x42", "rotate_right", {"relative_degrees": 70.49999237060547}),
    (3, 12, b"\x18\x61\x0a\x49\x01\x20\x05\x0b\x01\x21\xf4\x01\x55\x00\x39\xa5\x70\x75\xc2", "rotate_left", {"relative_degrees": -61.36000442504883}),
    # Gesture mode (not able to reproduce with my cube):
    (2, 18, b"\x18\x36\x0a\x55\x00\x21\x03\x00", "drop", {"value": 3}),
    (2, 18, b"\x18\x36\x0a\x55\x00\x21\x04\x02", "knock", {"value": 516, "activated_face": 5}),
    # Scene mode:
    (2, 18, b"\x18\x69\x0a\x55\x00\x21\x02\x04", "scene", {"value": 1026, "activated_face": 3}),
    # Secret Xiaomi cluster messages; not-yet-implemented
    # This is the status update event, which you get if you leave the cube idle, or if you press the button once:
    # (1, 64704,  b'\x1C\x5F\x11\x59\x0A\xF7\x00\x41\x3E\x01\x21\xFC\x0B\x03\x28\x19\x04\x21\xA8\x13\x05\x21\x09\x00\x06\x24\x1C\x00\x00\x00\x00\x08\x21\x1C\x01\x0A\x21\xEA\x14\x0C\x20\x01\x66\x20\x03\x67\x20\x01\x68\x21\xA8\x00\x97\x21\x00\x00\x98\x21\x00\x00\x99\x21\x00\x00\x9A\x21\x04\x00\x9B\x20\x01', None, None),
    # This is a mode change event, which you get if you push the button 6 times:
    # (1, 64704, b'\x18\x58\x0A\x48\x01\x20\x01', "mode_change", {"mode": 1}),
]
# fmt: on


@pytest.mark.parametrize(
    "endpoint_id, cluster_id, payload, expected_command, expected_args",
    test_cases,
)
async def test_cube_zha_events(
    cube_device, endpoint_id, cluster_id, payload, expected_command, expected_args
):
    """Test that raw Zigbee messages generate expected events."""

    # GIVEN: Dynamically find the right cluster and attach a listener
    cluster = cube_device.endpoints[endpoint_id].in_clusters[cluster_id]
    listener = MagicMock()
    cluster.add_listener(listener)

    # Formulate the incoming packet
    packet = ZigbeePacket(
        profile_id=0x0104,  # Home Automation Profile
        cluster_id=cluster_id,
        src_ep=endpoint_id,
        dst_ep=1,
        data=SerializableBytes(payload),
        dst=AddrModeAddress(
            addr_mode=AddrMode.NWK,
            address=cube_device.nwk,
        ),
    )

    # WHEN: The device receives the packet
    cube_device.packet_received(packet)

    # THEN: Exactly one ZHA event should be fired
    assert listener.zha_send_event.call_count == 1, (
        f"Expected 1 event, got {listener.zha_send_event.call_count}"
    )

    # Extract what was actually sent to Home Assistant
    fired_command, fired_args = listener.zha_send_event.call_args[0]

    # Assert it matches our table
    assert fired_command == expected_command
    assert fired_args == expected_args

    cluster.remove_listener(listener)
