"""Sunricher Button device."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP_ON_OFF,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    RIGHT,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

(
    QuirkBuilder("Sunricher", "ZGRC-KEY-004")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
            (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
            (LONG_PRESS, RIGHT): {COMMAND: COMMAND_MOVE_ON_OFF},
            (LONG_RELEASE, RIGHT): {COMMAND: COMMAND_STOP_ON_OFF},
        }
    )
    # Holding the on button dims up, holding the off button dims down, so a short
    # press can only be sent on release. The stop does not tell the buttons apart,
    # so it is classified by the hold.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END,
                trigger=(SHORT_PRESS, TURN_ON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE_ON_OFF,
                    CLUSTER_ID: LevelControl.cluster_id,
                    PARAMS: {"move_mode": LevelControl.MoveMode.Up},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, RIGHT),
                while_held=True,
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
                trigger=(SHORT_PRESS, TURN_OFF),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                event_data={
                    COMMAND: COMMAND_MOVE_ON_OFF,
                    CLUSTER_ID: LevelControl.cluster_id,
                    PARAMS: {"move_mode": LevelControl.MoveMode.Down},
                },
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, RIGHT),
                while_held=True,
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_off",
        translation_key="off_button",
        fallback_name="Off button",
    )
    .add_to_registry()
)
