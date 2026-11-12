"""Quirk for AwoX ERCU_WS_Zm remote control."""

from zigpy.zcl.clusters.general import LevelControl, OnOff, Scenes
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_RECALL,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STEP_ON_OFF,
    COMMAND_STORE,
    COMMAND_TOGGLE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    PARAMS,
    SHORT_PRESS,
    TOGGLE,
    TURN_OFF,
    TURN_ON,
)

(
    QuirkBuilder("AwoX", "ERCU_WS_Zm")
    .friendly_name(manufacturer="EGLO", model="Smart Switch Connect-Z")
    .device_automation_triggers(
        {
            # firmware up to 2.7.3 alternates on and off instead of toggle
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TOGGLE): {
                COMMAND: COMMAND_TOGGLE,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 1,
            },
            # step size is 36, firmware up to 2.7.2 uses 18
            (SHORT_PRESS, DIM_UP): {
                COMMAND: COMMAND_STEP_ON_OFF,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "step_mode": LevelControl.StepMode.Up,
                    "transition_time": 2,
                },
            },
            (SHORT_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_STEP,
                CLUSTER_ID: LevelControl.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "step_mode": LevelControl.StepMode.Down,
                    "transition_time": 2,
                },
            },
            # holding dim up cycles the hue, holding dim down steps the color temp,
            # the direction alternates with every hold
            (LONG_PRESS, "change_color"): {
                COMMAND: "move_to_hue_and_saturation",
                CLUSTER_ID: Color.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, "change_color_temp"): {
                COMMAND: COMMAND_STEP_COLOR_TEMP,
                CLUSTER_ID: Color.cluster_id,
                ENDPOINT_ID: 1,
            },
            # dim up + dim down, hold 3s to store
            (SHORT_PRESS, "recall_settings"): {
                COMMAND: COMMAND_RECALL,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"group_id": 0, "scene_id": 1},
            },
            (LONG_PRESS, "save_settings"): {
                COMMAND: COMMAND_STORE,
                CLUSTER_ID: Scenes.cluster_id,
                ENDPOINT_ID: 1,
                PARAMS: {"group_id": 0, "scene_id": 1},
            },
        }
    )
    .add_to_registry()
)
