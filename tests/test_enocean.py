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
from zigpy.zgp.types import ApplicationID, DeviceID, GPDCommandID, SrcID

import zhaquirks
from zhaquirks.enocean import CONTACT_A0, CONTACT_A1
from zhaquirks.enocean.ptm215z import PTM215ZButton
from zhaquirks.enocean.ptm216z import PTM216ZButton

zhaquirks.setup()

# Every press captured from a real PTM 216Z: the four contacts individually, both
# contacts of each rocker, and both diagonals
CAPTURED_PRESSES = [0x01, 0x04, 0x02, 0x08, 0x03, 0x0C, 0x05, 0x0A]


@pytest.fixture
def ptm216z(MockAppController):
    """Create the zigpy GPD for a PTM 216Z."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x0155F443),
    )
    gpd.device_id = DeviceID.GenericSwitch
    return gpd


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


@pytest.mark.parametrize("src_id", [0x01500000, 0x01511223, 0x0155F443, 0x015FFFFF])
def test_ptm216z_matches(MockAppController, src_id):
    """Test that the quirk matches a PTM 216Z anywhere in its SrcID block."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(src_id),
    )
    gpd.device_id = DeviceID.GenericSwitch

    entry = DEVICE_REGISTRY.match_green_power_entry(gpd)

    assert entry is not None
    assert entry.source.module == "zhaquirks.enocean.ptm216z"


def test_ptm216z_does_not_match_ptm215ze(MockAppController):
    """Test that the quirk ignores a PTM 215ZE in the same SrcID block."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x0155F443),
    )
    gpd.device_id = DeviceID.OnOffSwitch

    assert DEVICE_REGISTRY.match_green_power_entry(gpd) is None


def test_ptm216z_does_not_match_outside_src_id_block(MockAppController):
    """Test that the quirk ignores a GPD outside of the PTM 216Z SrcID block."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x01700001),
    )
    gpd.device_id = DeviceID.GenericSwitch

    assert DEVICE_REGISTRY.match_green_power_entry(gpd) is None


def test_ptm216z_entities(buttons):
    """Test that there is one entity per contact."""
    assert list(buttons) == ["button_a0", "button_a1", "button_b0", "button_b1"]
    assert [entity.event_types for entity in buttons.values()] == [
        [ButtonEventType.PRESS_START, ButtonEventType.PRESS_END]
    ] * 4


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

    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Press8BitVector,
            command=GPContactStatusPayload(contact_status=contact_status),
        ),
    )
    assert [event.unique_id.rsplit("-", 1)[-1] for event in events] == expected
    assert all(
        event.triggered.event_type == ButtonEventType.PRESS_START for event in events
    )
    assert events[0].triggered.event_attributes == {"contact_status": contact_status}

    events.clear()

    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Release8BitVector,
            command=GPContactStatusPayload(contact_status=0),
        ),
    )
    assert [event.unique_id.rsplit("-", 1)[-1] for event in events] == expected
    assert all(
        event.triggered.event_type == ButtonEventType.PRESS_END for event in events
    )


def test_ptm216z_ignored_commands(ptm216z, buttons):
    """Test that commands not changing the state of a contact fire nothing."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    # A release nothing was pressed for
    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Release8BitVector,
            command=GPContactStatusPayload(contact_status=0),
        ),
    )
    # A press zigpy could not parse
    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Press8BitVector,
            command=None,
        ),
    )
    # A command other than the 8-bit vector press and release
    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Toggle,
            command=GPContactStatusPayload(contact_status=CONTACT_A0),
        ),
    )

    assert events == []


def test_ptm216z_partial_release(ptm216z, buttons):
    """Test that a release only ends the presses of contacts that opened."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Press8BitVector,
            command=GPContactStatusPayload(contact_status=CONTACT_A0 | CONTACT_A1),
        ),
    )
    events.clear()

    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Release8BitVector,
            command=GPContactStatusPayload(contact_status=CONTACT_A1),
        ),
    )
    assert [
        (event.unique_id.rsplit("-", 1)[-1], event.triggered.event_type)
        for event in events
    ] == [("button_a0", ButtonEventType.PRESS_END)]

    events.clear()

    ptm216z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm216z.ieee),
            endpoint_id=None,
            command_id=GPDCommandID.Release8BitVector,
            command=GPContactStatusPayload(contact_status=0),
        ),
    )
    assert [
        (event.unique_id.rsplit("-", 1)[-1], event.triggered.event_type)
        for event in events
    ] == [("button_a1", ButtonEventType.PRESS_END)]


def test_ptm216z_captured_sequence(ptm216z, buttons):
    """Test the full captured sequence of presses, each followed by its release."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    for contact_status in CAPTURED_PRESSES:
        ptm216z.emit(
            GreenPowerCommandReceived.event_type,
            GreenPowerCommandReceived(
                device_ieee=str(ptm216z.ieee),
                endpoint_id=None,
                command_id=GPDCommandID.Press8BitVector,
                command=GPContactStatusPayload(contact_status=contact_status),
            ),
        )
        ptm216z.emit(
            GreenPowerCommandReceived.event_type,
            GreenPowerCommandReceived(
                device_ieee=str(ptm216z.ieee),
                endpoint_id=None,
                command_id=GPDCommandID.Release8BitVector,
                command=GPContactStatusPayload(contact_status=0),
            ),
        )

    presses = [
        e for e in events if e.triggered.event_type == ButtonEventType.PRESS_START
    ]
    releases = [
        e for e in events if e.triggered.event_type == ButtonEventType.PRESS_END
    ]

    # Four single-contact presses and four two-contact presses, each released once
    assert len(presses) == 4 + 2 * 4
    assert [e.unique_id for e in presses] == [e.unique_id for e in releases]


@pytest.fixture
def ptm215z(MockAppController):
    """Create the zigpy GPD for a PTM 215Z."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x01A41D99),
    )
    gpd.device_id = DeviceID.OnOffSwitch
    return gpd


@pytest.fixture
def ptm215z_buttons(ptm215z):
    """Create the PTM 215Z quirk's event entities, keyed by their unique ID suffix."""
    entry = DEVICE_REGISTRY.match_green_power_entry(ptm215z)
    zha_device = entry.zha_device_factory(ptm215z, MagicMock())

    assert zha_device.manufacturer == "EnOcean"
    assert zha_device.model == "PTM 215Z"

    entities = [
        entity
        for entity in zha_device.discover_entities()
        if isinstance(entity, PTM215ZButton)
    ]

    for entity in entities:
        entity.on_add()

    return {entity.unique_id.rsplit("-", 1)[-1]: entity for entity in entities}


@pytest.mark.parametrize(
    "src_id", [0x01700000, 0x01711F3E, 0x017FFFFF, 0x01A40000, 0x01A41D99, 0x01A4FFFF]
)
def test_ptm215z_matches(MockAppController, src_id):
    """Test that the quirk matches a PTM 215Z anywhere in its SrcID blocks."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(src_id),
    )
    gpd.device_id = DeviceID.OnOffSwitch

    entry = DEVICE_REGISTRY.match_green_power_entry(gpd)

    assert entry is not None
    assert entry.source.module == "zhaquirks.enocean.ptm215z"


@pytest.mark.parametrize(
    ("src_id", "device_id"),
    [
        # Outside of the SrcID blocks
        (0x016FFFFF, DeviceID.OnOffSwitch),
        (0x01800000, DeviceID.OnOffSwitch),
        (0x01A3FFFF, DeviceID.OnOffSwitch),
        (0x01A50000, DeviceID.OnOffSwitch),
        # A PTM 215ZE
        (0x0155F443, DeviceID.OnOffSwitch),
        # Not an on/off switch
        (0x01A41D99, DeviceID.GenericSwitch),
    ],
)
def test_ptm215z_does_not_match(MockAppController, src_id, device_id):
    """Test that the quirk ignores other GPDs."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(src_id),
    )
    gpd.device_id = device_id

    entry = DEVICE_REGISTRY.match_green_power_entry(gpd)

    assert entry is None or entry.source.module != "zhaquirks.enocean.ptm215z"


def test_ptm215z_entities(ptm215z_buttons):
    """Test that there is one entity per contact."""
    assert list(ptm215z_buttons) == ["button_a0", "button_a1", "button_b0", "button_b1"]
    assert [entity.event_types for entity in ptm215z_buttons.values()] == [
        [ButtonEventType.PRESS_START, ButtonEventType.PRESS_END]
    ] * 4


@pytest.mark.parametrize(
    ("press", "release", "expected"),
    [
        (GPDCommandID.RecallScene0, GPDCommandID.RecallScene4, ["button_a0"]),
        (GPDCommandID.RecallScene1, GPDCommandID.RecallScene5, ["button_a1"]),
        (GPDCommandID.RecallScene3, GPDCommandID.RecallScene7, ["button_b0"]),
        (GPDCommandID.RecallScene2, GPDCommandID.RecallScene6, ["button_b1"]),
        # Both top and both bottom contacts
        (GPDCommandID.Press2of2, GPDCommandID.Release2of2, ["button_a0", "button_b0"]),
        (GPDCommandID.Press1of2, GPDCommandID.Release1of2, ["button_a1", "button_b1"]),
    ],
)
def test_ptm215z_press_and_release(ptm215z, ptm215z_buttons, press, release, expected):
    """Test that a press and its release only fire the contacts that were pressed."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in ptm215z_buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    for command_id, event_type in [
        (press, ButtonEventType.PRESS_START),
        (release, ButtonEventType.PRESS_END),
    ]:
        ptm215z.emit(
            GreenPowerCommandReceived.event_type,
            GreenPowerCommandReceived(
                device_ieee=str(ptm215z.ieee),
                endpoint_id=None,
                command_id=command_id,
                command=None,
            ),
        )
        assert [
            (event.unique_id.rsplit("-", 1)[-1], event.triggered.event_type)
            for event in events
        ] == [(suffix, event_type) for suffix in expected]

        events.clear()


@pytest.mark.parametrize(
    "command_id",
    [
        # Commands not mapped to a contact, the energy bar among them
        GPDCommandID.Toggle,
        GPDCommandID.Press1of1,
        GPDCommandID.ShortPress2of2,
        GPDCommandID.Press8BitVector,
    ],
)
def test_ptm215z_ignored_commands(ptm215z, ptm215z_buttons, command_id):
    """Test that commands not reporting a contact fire nothing."""
    events: list[EntityEventTriggeredEvent] = []
    for entity in ptm215z_buttons.values():
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    ptm215z.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(ptm215z.ieee),
            endpoint_id=None,
            command_id=command_id,
            command=None,
        ),
    )

    assert events == []
