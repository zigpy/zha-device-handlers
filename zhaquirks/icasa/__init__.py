"""Module for icasa devices."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_STOP_ON_OFF,
    ENDPOINT_ID,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
)

# Both buttons stop their move when released, with or without on/off
_STOP_EVENTS = (
    ButtonEvent(
        event_type=ButtonEventType.LONG_PRESS_END,
        trigger=(LONG_RELEASE, BUTTON),
        while_held=True,
    ),
    ButtonEvent(
        event_type=ButtonEventType.LONG_PRESS_END,
        event_data={
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
        },
        while_held=True,
    ),
)

# Only the hold of the on and off buttons is mapped: when their short press is sent
# is not confirmed, so it is left out
ON_OFF_BUTTON_EVENT_ENTITIES = (
    ButtonEventMetadata(
        events=[
            # The held button is matched by direction only, not by the keypad's rate
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE_ON_OFF,
                    CLUSTER_ID: LevelControl.cluster_id,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 0},
                },
            ),
            *_STOP_EVENTS,
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_on",
        translation_key="on_button",
        fallback_name="On button",
    ),
    ButtonEventMetadata(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE_ON_OFF,
                    CLUSTER_ID: LevelControl.cluster_id,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 1},
                },
            ),
            # The off button may also move down without on/off
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE,
                    CLUSTER_ID: LevelControl.cluster_id,
                    ENDPOINT_ID: 1,
                    PARAMS: {"move_mode": 1},
                },
            ),
            *_STOP_EVENTS,
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_off",
        translation_key="off_button",
        fallback_name="Off button",
    ),
)


def scene_button_event_entities(count: int) -> tuple[ButtonEventMetadata, ...]:
    """Return the button event entities of the numbered scene buttons.

    A scene button recalls its scene when released after a short press. The scene
    store of a long press is left out, as when it is sent is not confirmed.
    """
    return tuple(
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, f"button_{number}"),
                ),
            ],
            cluster_id=Scenes.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix=f"button_{number}",
            translation_key="button_numbered",
            translation_placeholders={"number": str(number)},
            fallback_name=f"Button {number}",
        )
        for number in range(1, count + 1)
    )
