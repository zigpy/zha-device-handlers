"""Tests for the EnOcean quirks."""

from unittest.mock import MagicMock

import pytest
from zha.application.platforms.event import EntityEventTriggeredEvent
from zha.application.platforms.event.const import ButtonEventType
from zha.quirks import DEVICE_REGISTRY
from zigpy.device import (
    GreenPowerCommandReceived,
    GreenPowerDevice as ZigpyGreenPowerDevice,
)
from zigpy.zgp.commands import GPContactStatusPayload
from zigpy.zgp.types import ApplicationID, GPDCommandID, SrcID

import zhaquirks
from zhaquirks.enocean.ptm216z import PTM216ZButton

zhaquirks.setup()

# Every press captured from a real PTM 216Z: the four contacts individually, both
# contacts of each rocker, and both diagonals
CAPTURED_PRESSES = [0x01, 0x04, 0x02, 0x08, 0x03, 0x0C, 0x05, 0x0A]


@pytest.fixture
def ptm216z(MockAppController):
    """Create the zigpy GPD for a PTM 216Z."""
    return ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x0155F443),
    )


@pytest.fixture
def buttons(ptm216z):
    """Create the quirk's event entities, keyed by their unique ID suffix."""
    entry = DEVICE_REGISTRY.match_green_power_entry(ptm216z)
    zha_device = entry.zha_device_factory(ptm216z, MagicMock())

    entities = [
        entity
        for entity in zha_device.discover_entities()
        if isinstance(entity, PTM216ZButton)
    ]

    for entity in entities:
        entity.on_add()

    return {entity.unique_id.rsplit("-", 1)[-1]: entity for entity in entities}


def emit(device, command_id: GPDCommandID, contact_status: int) -> None:
    """Emit a GPD 8-bit vector command."""
    device.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(device.ieee),
            endpoint_id=None,
            command_id=command_id,
            command=GPContactStatusPayload(contact_status=contact_status),
        ),
    )


def test_ptm216z_matches(ptm216z):
    """Test that the quirk matches a PTM 216Z by its SrcID."""
    entry = DEVICE_REGISTRY.match_green_power_entry(ptm216z)

    assert entry is not None
    assert entry.source.module == "zhaquirks.enocean.ptm216z"


def test_ptm216z_does_not_match_other_vendors(MockAppController):
    """Test that the quirk ignores a GPD outside of EnOcean's SrcID block."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x01700001),
    )

    assert DEVICE_REGISTRY.match_green_power_entry(gpd) is None


def test_ptm216z_entities(buttons):
    """Test that there is one entity per contact."""
    assert list(buttons) == ["button_a0", "button_a1", "button_b0", "button_b1"]
    assert [entity.event_types for entity in buttons.values()] == [
        [ButtonEventType.PRESS_START, ButtonEventType.PRESS_END]
    ] * 4
    assert buttons["button_a0"].primary
    assert not any(entity.primary for entity in list(buttons.values())[1:])


@pytest.mark.parametrize(
    ("contact_status", "expected"),
    [
        (0x01, ["button_a0"]),
        (0x02, ["button_a1"]),
        (0x04, ["button_b0"]),
        (0x08, ["button_b1"]),
        # Both contacts of a rocker, and the two diagonals
        (0x03, ["button_a0", "button_a1"]),
        (0x0C, ["button_b0", "button_b1"]),
        (0x05, ["button_a0", "button_b0"]),
        (0x0A, ["button_a1", "button_b1"]),
    ],
)
def test_ptm216z_press_and_release(ptm216z, buttons, contact_status, expected):
    """Test that a press and its release only fire the contacts that were pressed."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    emit(ptm216z, GPDCommandID.Press8BitVector, contact_status)
    assert [event.unique_id.rsplit("-", 1)[-1] for event in events] == expected
    assert all(
        event.triggered.event_type == ButtonEventType.PRESS_START for event in events
    )
    assert events[0].triggered.event_attributes == {"contact_status": contact_status}

    events.clear()

    # The switch only reports that every contact is open again
    emit(ptm216z, GPDCommandID.Release8BitVector, 0)
    assert [event.unique_id.rsplit("-", 1)[-1] for event in events] == expected
    assert all(
        event.triggered.event_type == ButtonEventType.PRESS_END for event in events
    )


def test_ptm216z_release_without_press(ptm216z, buttons):
    """Test that a release nothing was pressed for fires nothing."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    emit(ptm216z, GPDCommandID.Release8BitVector, 0)

    assert events == []


def test_ptm216z_captured_sequence(ptm216z, buttons):
    """Test the full captured sequence of presses, each followed by its release."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    for contact_status in CAPTURED_PRESSES:
        emit(ptm216z, GPDCommandID.Press8BitVector, contact_status)
        emit(ptm216z, GPDCommandID.Release8BitVector, 0)

    presses = [
        e for e in events if e.triggered.event_type == ButtonEventType.PRESS_START
    ]
    releases = [
        e for e in events if e.triggered.event_type == ButtonEventType.PRESS_END
    ]

    # Four single-contact presses and four two-contact presses, each released once
    assert len(presses) == 4 + 2 * 4
    assert [e.unique_id for e in presses] == [e.unique_id for e in releases]
