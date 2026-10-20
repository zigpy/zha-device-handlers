"""Module for icasa devices."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_STOP_ON_OFF,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
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

# The short press of the on and off buttons is sent on release, as the same button
# sends a move when held
ON_OFF_BUTTON_EVENT_ENTITIES = (
    ButtonEventMetadata(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, TURN_ON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, DIM_UP),
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
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, TURN_OFF),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, DIM_DOWN),
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

    A scene button recalls its scene when released after a short press, and stores
    it when released after a long press.
    """
    return tuple(
        ButtonEventMetadata(
            events=[
                ButtonEvent(
                    event_type=ButtonEventType.PRESS_END,
                    trigger=(SHORT_PRESS, f"button_{number}"),
                ),
                ButtonEvent(
                    event_type=ButtonEventType.LONG_PRESS_END,
                    trigger=(LONG_PRESS, f"button_{number}"),
                ),
            ],
            cluster_id=Scenes.cluster_id,
            cluster_type=ClusterType.Client,
            unique_id_suffix=f"button_{number}",
            translation_key="numbered_button",
            translation_placeholders={"button_number": str(number)},
            fallback_name=f"Button {number}",
        )
        for number in range(1, count + 1)
    )
