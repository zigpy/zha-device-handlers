"""Tests for Nimly lock quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent, ClusterType
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import PowerConfiguration

import zhaquirks
from zhaquirks.nimly import NIMLY
from zhaquirks.nimly.lock import (
    NimlyDoorLock,
    last_action_converter,
    last_action_source_converter,
    last_action_user_converter,
)

zhaquirks.setup()


def test_last_action_source_converter() -> None:
    """Test the last action source converter for Nimly Door Lock cluster."""
    assert last_action_source_converter(0x00020001) == "zigbee", (
        "Expected 'zigbee' for value 0x00010001"
    )
    assert last_action_source_converter(0x03010001) == "fingerprint", (
        "Expected 'fingerprint' for value 0x03010001"
    )
    assert last_action_source_converter(0x99010001) is None, (
        "Expected None for value 0x99010001"
    )


def test_last_action_converter() -> None:
    """Test the last action converter for Nimly Door Lock cluster."""
    assert last_action_converter(0x0A010001) == "lock", (
        "Expected 'lock' for value 0x0a010001"
    )
    assert last_action_converter(0x00020001) == "unlock", (
        "Expected 'unlock' for value 0x00020001"
    )
    assert last_action_converter(0x01030001) is None, (
        "Expected None for value 0x01030001"
    )


def test_last_action_user_converter() -> None:
    """Test the last action user converter for Nimly Door Lock cluster."""
    assert last_action_user_converter(0x01020001) == 1, (
        "Expected user ID 1 for value 0x01020001"
    )
    assert last_action_user_converter(0x02020010) == 16, (
        "Expected user ID 16 for value 0x02020010"
    )


# Real NimlyCodePRO report of the last-operation attribute (#5235):
#   fc=0x08 -> no manufacturer code, server-to-client, default response enabled
#   TSN=0xc8, cmd=0x0a (Report_Attributes)
#   attr 0x0100 (bitmap32) = 0x02020001 (keypad, unlock, user 1)
LAST_ACTION_REPORT = b"\x08\xc8\x0a\x00\x01\x1b\x01\x00\x02\x02"

# The same report preceded by lock_state (0x0000, enum8) = 1 (locked)
LOCK_STATE_AND_LAST_ACTION_REPORT = (
    b"\x08\xc9\x0a\x00\x00\x30\x01\x00\x01\x1b\x01\x00\x02\x02"
)

# The last-operation report with the manufacturer code 0x1234 set (fc=0x0c)
MANUFACTURER_LAST_ACTION_REPORT = b"\x0c\x34\x12\xca\x0a\x00\x01\x1b\x01\x00\x02\x02"


def _nimly_lock(zigpy_device_from_v2_quirk, model: str):
    """Create a quirked Nimly lock and collect its door lock attribute events."""
    device = zigpy_device_from_v2_quirk(
        NIMLY,
        model,
        endpoint_ids=[11],
        cluster_ids={
            11: {
                DoorLock.cluster_id: ClusterType.Server,
                PowerConfiguration.cluster_id: ClusterType.Server,
            }
        },
    )
    door_lock = device.endpoints[11].door_lock
    assert isinstance(door_lock, NimlyDoorLock)

    events = []
    door_lock.on_event(AttributeReportedEvent.event_type, events.append)
    door_lock.on_event(AttributeUpdatedEvent.event_type, events.append)

    return device, door_lock, events


def _receive(device, data: bytes) -> None:
    """Receive a door lock frame from endpoint 11."""
    device.packet_received(
        t.ZigbeePacket(
            profile_id=zha.PROFILE_ID,
            cluster_id=DoorLock.cluster_id,
            src_ep=11,
            dst_ep=11,
            data=t.SerializableBytes(data),
        )
    )


@pytest.mark.parametrize("model", ["NimlyPRO24", "EasyCodeTouch"])
async def test_last_action_report_without_manufacturer_code(
    zigpy_device_from_v2_quirk, model: str
) -> None:
    """A report without a manufacturer code updates the last-action attribute."""
    device, door_lock, events = _nimly_lock(zigpy_device_from_v2_quirk, model)
    attr = NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source

    with mock.patch.object(door_lock, "send_default_rsp") as send_default_rsp:
        _receive(device, LAST_ACTION_REPORT)

    assert [e.attribute_name for e in events] == [attr.name]
    assert door_lock.get(attr.name) == 0x02020001

    # One default response, for the original frame without a manufacturer code
    assert send_default_rsp.call_count == 1
    assert send_default_rsp.mock_calls[0].args[0].manufacturer is None


async def test_mixed_report_without_manufacturer_code(
    zigpy_device_from_v2_quirk,
) -> None:
    """Standard attributes in the same report are still matched without a code."""
    device, door_lock, events = _nimly_lock(zigpy_device_from_v2_quirk, "NimlyPRO24")
    attr = NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source

    with mock.patch.object(door_lock, "send_default_rsp") as send_default_rsp:
        _receive(device, LOCK_STATE_AND_LAST_ACTION_REPORT)

    assert sorted(e.attribute_name for e in events) == sorted(
        [attr.name, DoorLock.AttributeDefs.lock_state.name]
    )
    assert door_lock.get(attr.name) == 0x02020001
    assert door_lock.get(DoorLock.AttributeDefs.lock_state.name) == (
        DoorLock.LockState.Locked
    )
    assert send_default_rsp.call_count == 1
    assert send_default_rsp.mock_calls[0].args[0].manufacturer is None


async def test_last_action_report_with_manufacturer_code(
    zigpy_device_from_v2_quirk,
) -> None:
    """A report with the manufacturer code set is matched as before."""
    device, door_lock, events = _nimly_lock(zigpy_device_from_v2_quirk, "NimlyPRO24")
    attr = NimlyDoorLock.AttributeDefs.nimly_last_lock_unlock_source

    _receive(device, MANUFACTURER_LAST_ACTION_REPORT)

    assert [e.attribute_name for e in events] == [attr.name]
    assert door_lock.get(attr.name) == 0x02020001
