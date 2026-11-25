"""Tests for rotary event entities of quirks v2."""

from typing import Any

import pytest
from zha.application import EntityPlatform, EntityType
from zha.application.platforms.event import ZhaEventRotary
from zha.quirks import DeviceRegistry
import zigpy.device
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

from tests.common import EventRecorder
from tests.test_quirks_v2_button_events import remote_device, send, v1_remote_quirk
import zhaquirks
from zhaquirks import _legacy_quirk_to_registry_entry
from zhaquirks.builder import (
    ButtonEvent,
    ButtonEventMetadata,
    ButtonEventType,
    QuirkBuilder,
    RotaryDirection,
    RotaryEvent,
    RotaryEventMetadata,
    RotaryEventType,
)
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STOP,
    ENDPOINT_ID,
    LEFT,
    RIGHT,
    ROTATED,
    SHORT_PRESS,
    TURN_ON,
)

zhaquirks.setup()


@pytest.fixture
def zigpy_device(MockAppController) -> zigpy.device.Device:
    """Return a remote with a push button and a dial on Level Control."""
    return remote_device(MockAppController)


TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
    (ROTATED, RIGHT): {COMMAND: COMMAND_STEP, "params": {"step_mode": 0}},
    (ROTATED, LEFT): {COMMAND: COMMAND_STEP, "params": {"step_mode": 1}},
}

# The `zha_event`s of a step, move and stop on Level Control
STEP_UP = {COMMAND: COMMAND_STEP, "params": {"step_mode": 0}}
STEP_DOWN = {COMMAND: COMMAND_STEP, "params": {"step_mode": 1}}
MOVE_UP = {COMMAND: COMMAND_MOVE, "params": {"move_mode": 0}}
STOP = {COMMAND: COMMAND_STOP}

DIAL_EVENTS = [
    RotaryEvent(
        event_type=RotaryEventType.ROTATION,
        trigger=(ROTATED, RIGHT),
        direction=RotaryDirection.CLOCKWISE,
        event_attributes_from_data={"steps": ["params", "step_size"]},
    ),
    RotaryEvent(
        event_type=RotaryEventType.ROTATION,
        event_data=STEP_DOWN,
        direction=RotaryDirection.COUNTER_CLOCKWISE,
        event_attributes={"pressed": False},
        event_attributes_from_data={"steps": ("args", 1)},
    ),
    RotaryEvent(
        event_type=RotaryEventType.ROTATION_START,
        event_data=MOVE_UP,
        direction=RotaryDirection.CLOCKWISE,
    ),
    RotaryEvent(event_type=RotaryEventType.ROTATION_END, event_data=STOP),
    # An integration-specific event type next to the standard ones
    RotaryEvent(
        event_type="mode_changed",
        event_data={COMMAND: COMMAND_OFF},
        event_attributes={"mode": "event"},
    ),
]


def dial_quirk() -> QuirkBuilder:
    """Return a quirk for a dial with a push button on the remote's clusters."""
    return (
        QuirkBuilder("manufacturer", "remote")
        .device_automation_triggers(TRIGGERS)
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, TURN_ON),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        )
        .rotary_event(
            events=DIAL_EVENTS,
            cluster_id=LevelControl.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="dial",
            translation_key="dial",
            fallback_name="Dial",
        )
    )


def rotary_quirk(
    *entities: tuple[str, list[ButtonEvent] | list[RotaryEvent]],
) -> QuirkBuilder:
    """Return a quirk for the remote with the given button and rotary entities."""
    builder = QuirkBuilder("manufacturer", "remote").device_automation_triggers(
        TRIGGERS
    )
    for suffix, events in entities:
        add_entity = (
            builder.rotary_event
            if isinstance(events[0], RotaryEvent)
            else builder.button_event
        )
        add_entity(
            events=events,
            cluster_id=LevelControl.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix=suffix,
            translation_key="dial",
            fallback_name="Dial",
        )
    return builder


def rotation(
    direction: RotaryDirection = RotaryDirection.CLOCKWISE, **kwargs: Any
) -> RotaryEvent:
    """Return a rotation event."""
    return RotaryEvent(
        event_type=RotaryEventType.ROTATION,
        direction=direction,
        **({"event_data": STEP_UP} | kwargs),
    )


async def test_rotary_event_metadata() -> None:
    """Test that the builder adds rotary event entity metadata."""
    entry = dial_quirk().add_to_registry(DeviceRegistry())

    button, dial = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(button, ButtonEventMetadata)
    assert isinstance(dial, RotaryEventMetadata)
    assert dial.entity_platform == EntityPlatform.EVENT
    assert dial.entity_type == EntityType.STANDARD
    assert dial.endpoint_id == 1
    assert dial.cluster_id == LevelControl.cluster_id
    assert dial.cluster_type == ClusterType.Client
    assert dial.unique_id_suffix == "dial"
    assert dial.translation_key == "dial"
    assert dial.fallback_name == "Dial"
    assert dial.events == tuple(DIAL_EVENTS)


async def test_rotary_event_entities(zigpy_device: zigpy.device.Device) -> None:
    """Test that a rotary event entity fires for the commands the dial sends."""
    registry = DeviceRegistry()
    dial_quirk().add_to_registry(registry)
    quirked = registry.resolve(zigpy_device)

    recorder = await EventRecorder.create(quirked)
    assert recorder.event_types() == {
        "button": ["press_end"],
        "dial": ["rotation", "rotation_start", "rotation_end", "mode_changed"],
    }

    entity = recorder.entities["dial"]
    assert isinstance(entity, ZhaEventRotary)
    assert entity.unique_id == "01:02:03:04:05:06:07:08-1-dial"
    assert entity.translation_key == "dial"
    assert entity.device_class is None
    assert entity.cluster is quirked.endpoints[1].out_clusters[LevelControl.cluster_id]

    # step(Up, 13), step(Down, 37), step(Down, 0), move(Up, 50), stop, on, off
    send(quirked, LevelControl.cluster_id, b"\x01\x01\x02\x00\x0d\x00\x00")
    send(quirked, LevelControl.cluster_id, b"\x01\x02\x02\x01\x25\x00\x00")
    send(quirked, LevelControl.cluster_id, b"\x01\x03\x02\x01\x00\x00\x00")
    send(quirked, LevelControl.cluster_id, b"\x01\x04\x01\x00\x32")
    send(quirked, LevelControl.cluster_id, b"\x01\x05\x03")
    send(quirked, OnOff.cluster_id, b"\x01\x06\x01")
    send(quirked, OnOff.cluster_id, b"\x01\x07\x00")

    assert recorder.pop() == [
        ("dial", "rotation", {"direction": "clockwise", "steps": 13}),
        (
            "dial",
            "rotation",
            {"direction": "counter_clockwise", "steps": 37, "pressed": False},
        ),
        # A step of 0 reports no movement
        ("dial", "rotation_start", {"direction": "clockwise"}),
        # The end of a turn gets the direction of its start
        ("dial", "rotation_end", {"direction": "clockwise"}),
        ("button", "press_end"),
        ("dial", "mode_changed", {"mode": "event"}),
    ]


async def test_rotary_event_trigger_missing_on_device(
    zigpy_device: zigpy.device.Device,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a rotary entity whose trigger the ZHA device lacks is skipped."""
    registry = DeviceRegistry()
    rotary_quirk(
        ("dial", [rotation(event_data=None, trigger=(ROTATED, RIGHT))]),
        ("dial_2", [rotation(event_data=STEP_DOWN)]),
    ).add_to_registry(registry)
    monkeypatch.setattr(
        QuirkV2Device, "device_automation_triggers", property(lambda self: {})
    )
    recorder = await EventRecorder.create(registry.resolve(zigpy_device))

    assert list(recorder.entities) == ["dial_2"]
    assert "has no device automation trigger" in caplog.text


def test_rotary_event_types() -> None:
    """Test that rotary events convert standard values and freeze their data."""
    event = RotaryEvent(
        event_type="rotation",
        trigger=[ROTATED, RIGHT],
        direction="clockwise",
        event_attributes={"extra": [1, {"a": [2]}]},
        event_attributes_from_data={"steps": ["args", 1]},
    )

    assert event == RotaryEvent(
        event_type=RotaryEventType.ROTATION,
        trigger=(ROTATED, RIGHT),
        direction=RotaryDirection.CLOCKWISE,
        event_attributes={"extra": (1, {"a": (2,)})},
        event_attributes_from_data={"steps": ("args", 1)},
    )
    assert isinstance(event.event_type, RotaryEventType)
    assert isinstance(event.direction, RotaryDirection)
    assert hash(event)

    # Other event types are integration-specific
    extra = RotaryEvent(event_type="rotation_stop", event_data=STOP)
    assert type(extra.event_type) is str


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"event_type": RotaryEventType.ROTATION_END}, "needs either a trigger or"),
        (
            {
                "event_type": RotaryEventType.ROTATION_END,
                "trigger": (ROTATED, RIGHT),
                "event_data": STOP,
            },
            "needs either a trigger or",
        ),
        (
            {"event_type": RotaryEventType.ROTATION_END, "trigger": (ROTATED,)},
            "pair of strings",
        ),
        (
            {"event_type": RotaryEventType.ROTATION_END, "event_data": {}},
            "matches every zha_event",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION_END,
                "event_data": {COMMAND: COMMAND_STOP, "endpoint": 1},
            },
            r"does not have \('endpoint'\)",
        ),
        ({"event_type": "", "event_data": STOP}, "Invalid event type ''"),
        (
            {"event_type": RotaryEventType.ROTATION, "trigger": (ROTATED, RIGHT)},
            "Event type rotation needs a direction",
        ),
        (
            {"event_type": RotaryEventType.ROTATION_START, "event_data": MOVE_UP},
            "Event type rotation_start needs a direction",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION_END,
                "event_data": STOP,
                "direction": "left",
            },
            "Invalid direction 'left'",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION_END,
                "event_data": STOP,
                "event_attributes": {"direction": "clockwise"},
            },
            "with `direction`, not as event data",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION_START,
                "event_data": MOVE_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes": {"steps": 1},
            },
            "Only 'rotation' reports an amount, not 'rotation_start'",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION_END,
                "event_data": STOP,
                "event_attributes_from_data": {"degrees": ["args", 0]},
            },
            "Only 'rotation' reports an amount, not 'rotation_end'",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes": {"steps": 1},
                "event_attributes_from_data": {"steps": ["args", 1]},
            },
            "sets the same event data twice",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes": {"steps": 0},
            },
            "Invalid steps 0",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes": {"degrees": True},
            },
            "Invalid degrees True",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes": {"pressed": 1},
            },
            "Invalid pressed 1",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes_from_data": {"steps": "args"},
            },
            "needs a non-empty sequence of keys and indexes",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes_from_data": {"steps": []},
            },
            "needs a non-empty sequence of keys and indexes",
        ),
        (
            {
                "event_type": RotaryEventType.ROTATION,
                "event_data": STEP_UP,
                "direction": RotaryDirection.CLOCKWISE,
                "event_attributes_from_data": {"steps": ["args", True]},
            },
            "Invalid key True in the path of event data steps",
        ),
    ],
)
def test_rotary_event_invalid(kwargs: dict, error: str) -> None:
    """Test that invalid rotary events are rejected, naming the event."""
    with pytest.raises(ValueError, match=error) as exc_info:
        RotaryEvent(**kwargs)

    # The pair of strings error names the trigger instead
    if "trigger" not in kwargs or len(kwargs["trigger"]) == 2:
        assert "RotaryEvent(" in str(exc_info.value)


@pytest.mark.parametrize(
    "kwargs",
    [{"event_attributes": [("steps", 1)]}, {"event_attributes_from_data": "steps"}],
)
def test_rotary_event_data_type(kwargs: dict) -> None:
    """Test that the event data of a rotary event has to be given as mappings."""
    with pytest.raises(TypeError, match="is a mapping of event data names"):
        rotation(**kwargs)


@pytest.mark.parametrize(
    ("events", "error"),
    [
        ([], "needs events"),
        (
            [RotaryEvent(event_type=RotaryEventType.ROTATION_END, event_data=STOP)],
            "needs 'rotation' or 'rotation_start'",
        ),
        (
            [RotaryEvent(event_type="rotate_right", event_data=STEP_UP)],
            "needs 'rotation' or 'rotation_start'",
        ),
    ],
)
def test_rotary_event_metadata_invalid(events: list[RotaryEvent], error: str) -> None:
    """Test that invalid rotary event entities are rejected."""
    with pytest.raises(ValueError, match=error):
        RotaryEventMetadata(
            events=events,
            cluster_id=LevelControl.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="dial",
            translation_key="dial",
            fallback_name="Dial",
        )


def test_rotary_event_metadata_required() -> None:
    """Test the required fields of a rotary event entity, which has no device class."""
    kwargs = {
        "events": [rotation()],
        "cluster_id": LevelControl.cluster_id,
        "cluster_type": ClusterType.Client,
        "unique_id_suffix": "dial",
        "translation_key": "dial",
        "fallback_name": "Dial",
    }

    for missing in ("cluster_type", "unique_id_suffix"):
        with pytest.raises(TypeError, match=missing):
            RotaryEventMetadata(**{k: v for k, v in kwargs.items() if k != missing})

    with pytest.raises(ValueError, match="unique_id_suffix"):
        RotaryEventMetadata(**{**kwargs, "unique_id_suffix": ""})

    with pytest.raises(ValueError, match="must have a translation_key"):
        RotaryEventMetadata(**{**kwargs, "translation_key": None})


async def test_rotary_event_unknown_trigger() -> None:
    """Test that a rotary event can only use triggers the quirk defines."""
    builder = QuirkBuilder("manufacturer", "remote").rotary_event(
        events=[rotation(event_data=None, trigger=(ROTATED, RIGHT))],
        cluster_id=LevelControl.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="dial",
        translation_key="dial",
        fallback_name="Dial",
    )

    with pytest.raises(ValueError, match="uses a device automation trigger"):
        builder.add_to_registry(DeviceRegistry())

    # Triggers can be added after the rotary event entity
    builder.device_automation_triggers(TRIGGERS).add_to_registry(DeviceRegistry())


def test_rotary_event_trigger_without_data() -> None:
    """Test that a rotary event cannot use a trigger matching every zha_event."""
    builder = rotary_quirk(
        ("dial", [rotation(event_data=None, trigger=(ROTATED, RIGHT))])
    ).device_automation_triggers({(ROTATED, RIGHT): {}})

    with pytest.raises(ValueError, match="trigger without data"):
        builder.add_to_registry(DeviceRegistry())


def test_rotary_event_duplicate_entity() -> None:
    """Test that button and rotary event entities share their unique IDs."""
    builder = rotary_quirk(
        ("dial", [rotation()]),
        (
            "dial",
            [
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
                )
            ],
        ),
    )

    with pytest.raises(ValueError, match="'dial' on endpoint 1 is defined twice"):
        builder.add_to_registry(DeviceRegistry())


@pytest.mark.parametrize(
    "events",
    [
        # The same trigger twice
        [
            rotation(event_data=None, trigger=(ROTATED, RIGHT)),
            rotation(
                RotaryDirection.COUNTER_CLOCKWISE,
                event_data=None,
                trigger=(ROTATED, RIGHT),
            ),
        ],
        # Event data matching every zha_event the trigger matches
        [
            rotation(event_data={COMMAND: COMMAND_STEP}),
            rotation(
                RotaryDirection.COUNTER_CLOCKWISE,
                event_data=None,
                trigger=(ROTATED, LEFT),
            ),
        ],
    ],
)
def test_rotary_event_never_fires(events: list[RotaryEvent]) -> None:
    """Test that a rotary event an earlier one of its entity covers is rejected."""
    with pytest.raises(ValueError, match="never fires"):
        rotary_quirk(("dial", events)).add_to_registry(DeviceRegistry())


@pytest.mark.parametrize(
    "button_event",
    [
        # A dial's press and its rotation can't share a match
        ButtonEvent(
            event_type=ButtonEventType.PRESS_END, event_data={COMMAND: COMMAND_STEP}
        ),
        ButtonEvent(event_type=ButtonEventType.PRESS_END, trigger=(ROTATED, RIGHT)),
        # A release while held still fires next to the rotary event
        ButtonEvent(
            event_type=ButtonEventType.LONG_PRESS_END,
            event_data={COMMAND: COMMAND_STEP},
            while_held=True,
        ),
    ],
)
def test_rotary_event_shared_with_button(button_event: ButtonEvent) -> None:
    """Test that a button and a rotary event entity cannot match the same event."""
    button_events = [button_event]
    if button_event.while_held:
        button_events.insert(
            0,
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={COMMAND: COMMAND_ON},
            ),
        )

    quirk = rotary_quirk(("dial", [rotation()]), ("button", button_events))

    with pytest.raises(ValueError, match="can match the same zha_event"):
        quirk.add_to_registry(DeviceRegistry())


def test_rotary_event_shared_between_entities() -> None:
    """Test that two rotary event entities cannot match the same event."""
    quirk = rotary_quirk(("dial", [rotation()]), ("dial_2", [rotation()]))

    with pytest.raises(ValueError, match="can match the same zha_event"):
        quirk.add_to_registry(DeviceRegistry())


V1_ROTARY_EVENT_ENTITIES = (
    RotaryEventMetadata(
        events=DIAL_EVENTS,
        cluster_id=LevelControl.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="dial",
        translation_key="dial",
        fallback_name="Dial",
    ),
)
V1_BUTTON_EVENT_ENTITIES = (
    ButtonEventMetadata(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
            )
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    ),
)


async def test_v1_rotary_event_entities(zigpy_device: zigpy.device.Device) -> None:
    """Test that a v1 quirk exposes button and rotary event entities together."""
    quirk = v1_remote_quirk(
        device_automation_triggers=TRIGGERS,
        button_event_entities=V1_BUTTON_EVENT_ENTITIES,
        rotary_event_entities=V1_ROTARY_EVENT_ENTITIES,
    )
    entry = _legacy_quirk_to_registry_entry(quirk)
    assert entry.zha_device_factory.quirk_definition.entity_metadata == (
        *V1_BUTTON_EVENT_ENTITIES,
        *V1_ROTARY_EVENT_ENTITIES,
    )

    registry = DeviceRegistry()
    registry.register(entry)
    quirked = registry.resolve(zigpy_device)
    assert isinstance(quirked, quirk)

    recorder = await EventRecorder.create(quirked)
    assert isinstance(recorder.zha_device, QuirkV2Device)
    assert list(recorder.entities) == ["button", "dial"]

    # step(Up, 13), stop, on
    send(quirked, LevelControl.cluster_id, b"\x01\x01\x02\x00\x0d\x00\x00")
    send(quirked, LevelControl.cluster_id, b"\x01\x02\x03")
    send(quirked, OnOff.cluster_id, b"\x01\x03\x01")

    assert recorder.pop() == [
        ("dial", "rotation", {"direction": "clockwise", "steps": 13}),
        ("dial", "rotation_end", {"direction": "clockwise"}),
        ("button", "press_end"),
    ]


def test_v1_rotary_event_entities_only() -> None:
    """Test that rotary event entities alone give a v1 quirk the quirks v2 device."""
    quirk = v1_remote_quirk(
        device_automation_triggers=TRIGGERS,
        rotary_event_entities=V1_ROTARY_EVENT_ENTITIES,
    )

    definition = _legacy_quirk_to_registry_entry(quirk).zha_device_factory
    assert definition.quirk_definition.entity_metadata == V1_ROTARY_EVENT_ENTITIES


def test_v1_rotary_event_unknown_trigger() -> None:
    """Test that a v1 rotary event can only use triggers the quirk defines."""
    quirk = v1_remote_quirk(rotary_event_entities=V1_ROTARY_EVENT_ENTITIES)

    with pytest.raises(ValueError, match="uses a device automation trigger"):
        _legacy_quirk_to_registry_entry(quirk)


def test_v1_rotary_event_shared_with_button() -> None:
    """Test that v1 button and rotary event entities cannot share data."""
    button = ButtonEventMetadata(
        events=[
            ButtonEvent(event_type=ButtonEventType.PRESS_END, event_data=STEP_DOWN)
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )
    quirk = v1_remote_quirk(
        device_automation_triggers=TRIGGERS,
        button_event_entities=(button,),
        rotary_event_entities=V1_ROTARY_EVENT_ENTITIES,
    )

    with pytest.raises(ValueError, match="can match the same zha_event"):
        _legacy_quirk_to_registry_entry(quirk)


def test_v1_rotary_event_duplicate_entity() -> None:
    """Test that v1 button and rotary event entities cannot share a unique ID."""
    button = ButtonEventMetadata(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
            )
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="dial",
        translation_key="button",
        fallback_name="Button",
    )
    quirk = v1_remote_quirk(
        device_automation_triggers=TRIGGERS,
        button_event_entities=(button,),
        rotary_event_entities=V1_ROTARY_EVENT_ENTITIES,
    )

    with pytest.raises(ValueError, match="'dial' on endpoint 1 is defined twice"):
        _legacy_quirk_to_registry_entry(quirk)
