"""IKEA Bilresa 2 button remote control."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, IkeaBilresaLevelControl, ScenesCluster

(
    QuirkBuilder(IKEA, "09B9")
    .replaces(ScenesCluster, cluster_type=ClusterType.Client)
    .replace_cluster_occurrences(IkeaBilresaLevelControl)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: "move_up_release",
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
            (LONG_RELEASE, DIM_DOWN): {
                COMMAND: "move_down_release",
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, DIM_UP): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 256,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (DOUBLE_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 257,
                    "param2": 13,
                    "param3": 0,
                },
            },
        }
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, TURN_ON),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, DIM_UP),
                press_count=2,
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
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, TURN_OFF),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, DIM_DOWN),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, DIM_DOWN),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, DIM_DOWN),
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
