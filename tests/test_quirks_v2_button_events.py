"""Tests for button event entities of quirks v2."""

import pytest
from zha.application import EntityPlatform, EntityType, Platform
from zha.application.platforms.event import ZhaEventButton
from zha.quirks import DeviceRegistry
import zigpy.device
import zigpy.profiles.zha
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, LevelControl, OnOff

from tests.common import ButtonEventRecorder
from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.builder.discovery import QUIRKS_ENTITY_META_TO_ENTITY_CLASS
from zhaquirks.builder.metadata import ButtonEventMetadata
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
    (LONG_PRESS, DIM_UP): {
        COMMAND: COMMAND_MOVE_ON_OFF,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        "params": {"move_mode": LevelControl.MoveMode.Up},
    },
    (LONG_RELEASE, DIM_UP): {COMMAND: COMMAND_STOP, CLUSTER_ID: 8, ENDPOINT_ID: 1},
    (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
}


@pytest.fixture
def zigpy_device(MockAppController) -> zigpy.device.Device:
    """Return a two button remote."""
    device = zigpy.device.Device(
        MockAppController, t.EUI64.convert("01:02:03:04:05:06:07:08"), 0x1234
    )
    device.manufacturer = "manufacturer"
    device.model = "remote"

    endpoint = device.add_endpoint(1)
    endpoint.profile_id = zigpy.profiles.zha.PROFILE_ID
    endpoint.device_type = zigpy.profiles.zha.DeviceType.NON_COLOR_CONTROLLER
    endpoint.add_input_cluster(Basic.cluster_id)
    endpoint.add_output_cluster(OnOff.cluster_id)
    endpoint.add_output_cluster(LevelControl.cluster_id)

    return device


def remote_quirk() -> QuirkBuilder:
    """Return a quirk for the remote with one button event entity per button."""
    return (
        QuirkBuilder("manufacturer", "remote")
        .device_automation_triggers(TRIGGERS)
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, TURN_ON),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    trigger=(LONG_PRESS, DIM_UP),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, DIM_UP),
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button_on",
            translation_key="on_button",
            fallback_name="On button",
        )
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_OFF, CLUSTER_ID: 6},
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button_off",
            translation_key="off_button",
            fallback_name="Off button",
        )
    )


def send(zigpy_device: zigpy.device.Device, cluster_id: int, payload: bytes) -> None:
    """Receive a ZCL frame from endpoint 1 of the device."""
    zigpy_device.packet_received(
        t.ZigbeePacket(
            src_ep=1,
            dst_ep=1,
            tsn=payload[1],
            profile_id=zigpy.profiles.zha.PROFILE_ID,
            cluster_id=cluster_id,
            data=t.SerializableBytes(payload),
        )
    )


async def test_button_event_metadata(zigpy_device: zigpy.device.Device) -> None:
    """Test that the builder adds button event entity metadata."""
    registry = DeviceRegistry()
    entry = remote_quirk().add_to_registry(registry)

    on_button, off_button = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(on_button, ButtonEventMetadata)
    assert on_button.entity_platform == EntityPlatform.EVENT
    assert on_button.entity_type == EntityType.STANDARD
    assert on_button.endpoint_id == 1
    assert on_button.cluster_id == OnOff.cluster_id
    assert on_button.cluster_type == ClusterType.Client
    assert on_button.unique_id_suffix == "button_on"
    assert on_button.translation_key == "on_button"
    assert on_button.fallback_name == "On button"
    assert [event.event_type for event in on_button.events] == [
        "press_end",
        "long_press_start",
        "long_press_end",
    ]
    assert off_button.events == (
        ButtonEvent(
            event_type=ButtonEventType.PRESS_END,
            event_data={COMMAND: COMMAND_OFF, CLUSTER_ID: 6},
        ),
    )


async def test_button_event_entities(zigpy_device: zigpy.device.Device) -> None:
    """Test that button event entities fire for the commands the remote sends."""
    registry = DeviceRegistry()
    remote_quirk().add_to_registry(registry)
    quirked = registry.resolve(zigpy_device)

    recorder = await ButtonEventRecorder.create(quirked)
    assert recorder.event_types() == {
        "button_on": ["press_end", "long_press_start", "long_press_end"],
        "button_off": ["press_end"],
    }

    entity = recorder.entities["button_on"]
    assert entity.unique_id == "01:02:03:04:05:06:07:08-1-button_on"
    assert entity.translation_key == "on_button"
    assert entity.cluster is quirked.endpoints[1].out_clusters[OnOff.cluster_id]

    # on, move_with_on_off(Up, 50), move_with_on_off(Down, 50), stop, off
    send(quirked, OnOff.cluster_id, b"\x01\x01\x01")
    send(quirked, LevelControl.cluster_id, b"\x01\x02\x05\x00\x32")
    send(quirked, LevelControl.cluster_id, b"\x01\x03\x05\x01\x32")
    send(quirked, LevelControl.cluster_id, b"\x01\x04\x03")
    send(quirked, OnOff.cluster_id, b"\x01\x05\x00")

    assert recorder.pop() == [
        ("button_on", "press_end"),
        ("button_on", "long_press_start"),
        ("button_on", "long_press_end"),
        ("button_off", "press_end"),
    ]


async def test_button_event_multi_press(zigpy_device: zigpy.device.Device) -> None:
    """Test that a multi press carries its press count."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("manufacturer", "remote")
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.SINGLE_PRESS,
                    event_data={COMMAND: COMMAND_ON},
                ),
                ButtonEvent(
                    event_type=ButtonEventType.MULTI_PRESS,
                    event_data={COMMAND: COMMAND_OFF},
                    press_count=2,
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        )
        .add_to_registry(registry)
    )

    recorder = await ButtonEventRecorder.create(registry.resolve(zigpy_device))

    send(recorder.zha_device.device, OnOff.cluster_id, b"\x01\x01\x01")
    send(recorder.zha_device.device, OnOff.cluster_id, b"\x01\x02\x00")

    assert recorder.pop() == [
        ("button", "single_press"),
        ("button", "multi_press", {"press_count": 2}),
    ]


async def test_button_event_hold(zigpy_device: zigpy.device.Device) -> None:
    """Test that repeated holds and releases while held reach the entity."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("manufacturer", "remote")
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    event_data={COMMAND: COMMAND_MOVE_ON_OFF},
                    repeats=True,
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    event_data={COMMAND: COMMAND_OFF},
                    while_held=True,
                ),
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_OFF},
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        )
        .add_to_registry(registry)
    )

    recorder = await ButtonEventRecorder.create(registry.resolve(zigpy_device))
    device = recorder.zha_device.device

    # off, move_with_on_off(Up, 50) twice, off
    send(device, OnOff.cluster_id, b"\x01\x01\x00")
    send(device, LevelControl.cluster_id, b"\x01\x02\x05\x00\x32")
    send(device, LevelControl.cluster_id, b"\x01\x03\x05\x00\x32")
    send(device, OnOff.cluster_id, b"\x01\x04\x00")

    assert recorder.pop() == [
        ("button", "press_end"),
        ("button", "long_press_start"),
        ("button", "long_press_end"),
    ]


async def test_button_event_missing_cluster(
    zigpy_device: zigpy.device.Device, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that a button event entity needs its cluster on the device."""
    registry = DeviceRegistry()
    (
        QuirkBuilder("manufacturer", "remote")
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_ON},
                ),
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Server,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        )
        .add_to_registry(registry)
    )

    recorder = await ButtonEventRecorder.create(registry.resolve(zigpy_device))

    assert recorder.entities == {}
    assert "does not have a cluster with id: 6" in caplog.text


async def test_button_event_unknown_trigger() -> None:
    """Test that a button event can only use triggers the quirk defines."""
    builder = QuirkBuilder("manufacturer", "remote").button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, TURN_OFF),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )

    with pytest.raises(ValueError, match="uses a device automation trigger"):
        builder.add_to_registry(DeviceRegistry())

    # Triggers can be added after the button event entity
    builder.device_automation_triggers(TRIGGERS).add_to_registry(DeviceRegistry())


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"event_type": ButtonEventType.PRESS_END}, "needs either a trigger or"),
        (
            {
                "event_type": ButtonEventType.PRESS_END,
                "trigger": (SHORT_PRESS, TURN_ON),
                "event_data": {COMMAND: COMMAND_ON},
            },
            "needs either a trigger or",
        ),
        (
            {"event_type": ButtonEventType.MULTI_PRESS, "trigger": (SHORT_PRESS, "")},
            "A press count is required",
        ),
        (
            {
                "event_type": ButtonEventType.SINGLE_PRESS,
                "trigger": (SHORT_PRESS, TURN_ON),
                "press_count": 2,
            },
            "A press count is required",
        ),
        (
            {
                "event_type": ButtonEventType.MULTI_PRESS,
                "trigger": (SHORT_PRESS, TURN_ON),
                "press_count": 1,
            },
            "needs at least two presses",
        ),
        (
            {
                "event_type": ButtonEventType.MULTI_PRESS,
                "trigger": (SHORT_PRESS, TURN_ON),
                "press_count": True,
            },
            "needs at least two presses",
        ),
        (
            {
                "event_type": ButtonEventType.PRESS_END,
                "trigger": (SHORT_PRESS, TURN_ON),
                "repeats": True,
            },
            "Only 'long_press_start' can repeat",
        ),
        (
            {
                "event_type": ButtonEventType.PRESS_END,
                "trigger": (SHORT_PRESS, TURN_ON),
                "while_held": True,
            },
            "Only 'long_press_end' can match while held",
        ),
    ],
)
def test_button_event_invalid(kwargs: dict, error: str) -> None:
    """Test that invalid button events are rejected."""
    with pytest.raises(ValueError, match=error):
        ButtonEvent(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"events": []}, "needs events"),
        (
            {
                "events": [
                    ButtonEvent(
                        event_type=ButtonEventType.MULTI_PRESS,
                        trigger=(SHORT_PRESS, TURN_ON),
                        press_count=2,
                    )
                ]
            },
            "only allowed together with 'single_press'",
        ),
        (
            {
                "events": [
                    ButtonEvent(
                        event_type=ButtonEventType.LONG_PRESS_END,
                        trigger=(SHORT_PRESS, TURN_ON),
                        while_held=True,
                    )
                ]
            },
            "Matching while held needs a 'long_press_start'",
        ),
        (
            {
                "events": [
                    ButtonEvent(
                        event_type=ButtonEventType.LONG_PRESS_START,
                        trigger=(SHORT_PRESS, TURN_ON),
                        repeats=True,
                    )
                ]
            },
            "needs another event type ending the hold",
        ),
    ],
)
def test_button_event_metadata_invalid(kwargs: dict, error: str) -> None:
    """Test that invalid button event entities are rejected."""
    with pytest.raises(ValueError, match=error):
        ButtonEventMetadata(
            **{
                "entity_platform": EntityPlatform.EVENT,
                "entity_type": EntityType.STANDARD,
                "cluster_id": OnOff.cluster_id,
                "cluster_type": ClusterType.Client,
                "unique_id_suffix": "button",
                "translation_key": "button",
                "fallback_name": "Button",
                **kwargs,
            }
        )


def test_button_event_metadata_required() -> None:
    """Test that a button event entity needs a cluster type and a unique ID suffix."""
    kwargs = {
        "events": [
            ButtonEvent(event_type=ButtonEventType.PRESS_END, event_data={COMMAND: 1})
        ],
        "cluster_id": OnOff.cluster_id,
        "cluster_type": ClusterType.Client,
        "unique_id_suffix": "button",
        "translation_key": "button",
        "fallback_name": "Button",
    }

    for missing in ("cluster_type", "unique_id_suffix"):
        with pytest.raises(TypeError, match=missing):
            ButtonEventMetadata(**{k: v for k, v in kwargs.items() if k != missing})

    with pytest.raises(TypeError, match="unique_id_suffix"):
        ButtonEventMetadata(**{**kwargs, "unique_id_suffix": None})

    with pytest.raises(ValueError, match="unique_id_suffix"):
        ButtonEventMetadata(**{**kwargs, "unique_id_suffix": ""})


def test_button_event_types() -> None:
    """Test that button events only take standard event types and valid triggers."""
    assert ButtonEvent(
        event_type="press_end", trigger=[SHORT_PRESS, TURN_ON]
    ) == ButtonEvent(
        event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
    )

    with pytest.raises(ValueError, match="long_pres_start"):
        ButtonEvent(event_type="long_pres_start", trigger=(SHORT_PRESS, TURN_ON))

    with pytest.raises(ValueError, match="pair of strings"):
        ButtonEvent(event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS,))

    with pytest.raises(ValueError, match="pair of strings"):
        ButtonEvent(event_type=ButtonEventType.PRESS_END, trigger="ab")

    with pytest.raises(ValueError, match="pair of strings"):
        ButtonEvent(event_type=ButtonEventType.PRESS_END, trigger=5)

    with pytest.raises(ValueError, match="matches every zha_event"):
        ButtonEvent(event_type=ButtonEventType.PRESS_END, event_data={})


async def test_button_event_duplicate_entity() -> None:
    """Test that a quirk cannot define a button event entity twice."""
    builder = remote_quirk().button_event(
        events=[
            ButtonEvent(event_type=ButtonEventType.PRESS_END, event_data={COMMAND: 1})
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_on",
        translation_key="on_button",
        fallback_name="On button",
    )

    with pytest.raises(ValueError, match="'button_on' on endpoint 1 is defined twice"):
        builder.add_to_registry(DeviceRegistry())


async def test_button_event_trigger_without_data() -> None:
    """Test that a button event cannot use a trigger matching every zha_event."""
    builder = (
        QuirkBuilder("manufacturer", "remote")
        .device_automation_triggers({(SHORT_PRESS, TURN_ON): {}})
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, TURN_ON),
                )
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        )
    )

    with pytest.raises(ValueError, match="trigger without data"):
        builder.add_to_registry(DeviceRegistry())


async def test_button_event_failing_entity(
    zigpy_device: zigpy.device.Device,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that an entity failing to be created does not drop the others."""

    class FailingButton(ZhaEventButton):
        """Button event entity failing for the on button."""

        def __init__(self, *args, unique_id_suffix: str, **kwargs) -> None:
            if unique_id_suffix == "button_on":
                raise RuntimeError("entity failed")
            super().__init__(*args, unique_id_suffix=unique_id_suffix, **kwargs)

    monkeypatch.setitem(
        QUIRKS_ENTITY_META_TO_ENTITY_CLASS,
        (Platform.EVENT, ButtonEventMetadata),
        FailingButton,
    )

    registry = DeviceRegistry()
    remote_quirk().add_to_registry(registry)
    recorder = await ButtonEventRecorder.create(registry.resolve(zigpy_device))

    assert list(recorder.entities) == ["button_off"]
    assert "failed to create entity" in caplog.text
    assert "entity failed" in caplog.text


def test_button_event_frozen() -> None:
    """Test that button event data is frozen."""
    event = ButtonEvent(
        event_type=ButtonEventType.PRESS_END,
        event_data={COMMAND: COMMAND_ON, "args": [1, 2], "params": {"a": [3]}},
    )

    assert event.event_data == {
        COMMAND: COMMAND_ON,
        "args": (1, 2),
        "params": {"a": (3,)},
    }
    assert hash(event)


@pytest.mark.parametrize("event_data", [[COMMAND_ON], COMMAND_ON, 1])
def test_button_event_event_data_type(event_data) -> None:
    """Test that button event data has to be a mapping."""
    with pytest.raises(TypeError, match="is a mapping of zha_event keys"):
        ButtonEvent(event_type=ButtonEventType.PRESS_END, event_data=event_data)


@pytest.mark.parametrize(
    "event_data",
    [
        {COMMAND: COMMAND_ON, "params": {}},
        {COMMAND: COMMAND_ON, "params": {"a": {}}},
        {COMMAND: COMMAND_ON, "args": [{}]},
    ],
)
def test_button_event_event_data_empty_mapping(event_data) -> None:
    """Test that button event data cannot hold a mapping matching any value."""
    with pytest.raises(ValueError, match="empty mapping matches any mapping"):
        ButtonEvent(event_type=ButtonEventType.PRESS_END, event_data=event_data)


def test_button_event_event_data_unknown_key() -> None:
    """Test that button event data can only use the keys of a `zha_event`."""
    with pytest.raises(ValueError, match=r"does not have \('endpoint'\)"):
        ButtonEvent(
            event_type=ButtonEventType.PRESS_END,
            event_data={COMMAND: COMMAND_ON, "endpoint": 1},
        )


async def test_button_event_trigger_unknown_key() -> None:
    """Test that a button event cannot use a trigger with keys no zha_event has."""
    builder = (
        QuirkBuilder("manufacturer", "remote")
        .device_automation_triggers({(SHORT_PRESS, TURN_ON): {"cmd": COMMAND_ON}})
        .button_event(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, TURN_ON),
                )
            ],
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix="button",
            translation_key="button",
            fallback_name="Button",
        )
    )

    with pytest.raises(ValueError, match=r"does not have \('cmd'\)"):
        builder.add_to_registry(DeviceRegistry())


def button_quirk(
    *buttons: tuple[str, list[ButtonEvent]], endpoint_ids: tuple[int, ...] = ()
) -> QuirkBuilder:
    """Return a quirk for the remote with the given button event entities."""
    builder = QuirkBuilder("manufacturer", "remote").device_automation_triggers(
        {**TRIGGERS, (SHORT_PRESS, "args"): {COMMAND: COMMAND_ON, "args": [1]}}
    )
    for index, (suffix, events) in enumerate(buttons):
        builder.button_event(
            events=events,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Client,
            endpoint_id=endpoint_ids[index] if endpoint_ids else 1,
            unique_id_suffix=suffix,
            translation_key="button",
            fallback_name="Button",
        )
    return builder


HOLD = ButtonEvent(
    event_type=ButtonEventType.LONG_PRESS_START, trigger=(LONG_PRESS, DIM_UP)
)


@pytest.mark.parametrize(
    "events",
    [
        # The same trigger twice
        [
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
            ),
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS, trigger=(SHORT_PRESS, TURN_ON)
            ),
        ],
        # Event data matching every zha_event the trigger matches, and more
        [
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, event_data={COMMAND: COMMAND_ON}
            ),
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS, trigger=(SHORT_PRESS, TURN_ON)
            ),
        ],
        # Event data without params covers the same command with params
        [
            HOLD,
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                event_data={COMMAND: COMMAND_MOVE_ON_OFF},
            ),
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_MOVE_ON_OFF, "params": {"move_mode": 0}},
            ),
        ],
        # Trigger data keeps lists, which cover the same items in a tuple
        [
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, "args")
            ),
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                event_data={COMMAND: COMMAND_ON, "args": (1,), CLUSTER_ID: 6},
            ),
        ],
        # Two matches while held, the broader one first
        [
            HOLD,
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                event_data={COMMAND: COMMAND_STOP},
                while_held=True,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, DIM_UP),
                while_held=True,
            ),
        ],
    ],
)
def test_button_event_never_fires(events: list[ButtonEvent]) -> None:
    """Test that a button event an earlier one of its entity covers is rejected."""
    with pytest.raises(ValueError, match="never fires"):
        button_quirk(("button", events)).add_to_registry(DeviceRegistry())


def test_button_event_while_held_first() -> None:
    """Test that a match while held does not hide the same data otherwise."""
    button_quirk(
        (
            "button",
            [
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(LONG_RELEASE, DIM_UP),
                ),
                HOLD,
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, DIM_UP),
                    while_held=True,
                ),
            ],
        )
    ).add_to_registry(DeviceRegistry())

    # Two matches while held, the narrower one first
    button_quirk(
        (
            "button",
            [
                HOLD,
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_RELEASE, DIM_UP),
                    while_held=True,
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    event_data={COMMAND: COMMAND_STOP},
                    while_held=True,
                ),
            ],
        )
    ).add_to_registry(DeviceRegistry())

    # A more specific match before a less specific one still fires
    button_quirk(
        (
            "button",
            [
                ButtonEvent(
                    event_type=ButtonEventType.SINGLE_PRESS,
                    trigger=(SHORT_PRESS, TURN_ON),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_ON},
                ),
            ],
        )
    ).add_to_registry(DeviceRegistry())


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
            ),
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
            ),
        ),
        # Neither covers the other, but an `on` from endpoint 1 matches both
        (
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_ON, CLUSTER_ID: 6},
            ),
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                event_data={COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
            ),
        ),
        # Only one of them matches while held
        (
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, event_data={COMMAND: COMMAND_STOP}
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, DIM_UP),
                while_held=True,
            ),
        ),
    ],
)
def test_button_event_shared_between_entities(
    first: ButtonEvent, second: ButtonEvent
) -> None:
    """Test that the events of two entities cannot match the same `zha_event`."""
    second_events = [second] if not second.while_held else [HOLD, second]
    quirk = button_quirk(("button_1", [first]), ("button_2", second_events))

    with pytest.raises(ValueError, match="can match the same zha_event"):
        quirk.add_to_registry(DeviceRegistry())


def test_button_event_shared_between_endpoints() -> None:
    """Test that entities with the same suffix on two endpoints cannot share data."""
    press = ButtonEvent(
        event_type=ButtonEventType.PRESS_END, event_data={COMMAND: COMMAND_ON}
    )
    quirk = button_quirk(("button", [press]), ("button", [press]), endpoint_ids=(1, 2))

    with pytest.raises(
        ValueError, match=r"'button' \(endpoint 1\) and .* \(endpoint 2\) can match"
    ):
        quirk.add_to_registry(DeviceRegistry())


def test_button_event_distinct_between_entities() -> None:
    """Test that entities may share releases while held, and distinct data."""
    release = ButtonEvent(
        event_type=ButtonEventType.LONG_PRESS_END,
        event_data={COMMAND: COMMAND_STOP},
        while_held=True,
    )
    button_quirk(
        (
            "button_up",
            [
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    event_data={
                        COMMAND: COMMAND_MOVE_ON_OFF,
                        "params": {"move_mode": 0},
                    },
                ),
                release,
            ],
        ),
        (
            "button_down",
            [
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_START,
                    event_data={
                        COMMAND: COMMAND_MOVE_ON_OFF,
                        "params": {"move_mode": 1},
                    },
                ),
                release,
            ],
        ),
        (
            "button_on",
            [
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_ON, "args": (1,)},
                )
            ],
        ),
        (
            "button_off",
            [
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: COMMAND_ON, "args": (1, 2)},
                )
            ],
        ),
        (
            "button_toggle",
            [
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: "toggle", "params": {"a": 1}},
                )
            ],
        ),
        (
            "button_toggle_2",
            [
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    event_data={COMMAND: "toggle", "params": 1},
                )
            ],
        ),
    ).add_to_registry(DeviceRegistry())
