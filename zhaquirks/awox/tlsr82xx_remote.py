"""AwoX remote controller quirk."""

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.foundation import ZCLCommandDef

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STOP,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

AWOX_CLUSTER_ID_1 = 65360
AWOX_CLUSTER_ID_2 = 65361


class AwoxLevelControlCluster(CustomCluster, LevelControl):
    """AwoX Custom Level Control Cluster for processing manufacturer specific commands."""

    class ServerCommandDefs(LevelControl.ServerCommandDefs):
        """Server command definitions."""

        awox_refresh = ZCLCommandDef(
            id=0x10,
            schema={
                "param1": t.uint8_t,
                "param2": t.uint8_t,
            },
            is_manufacturer_specific=False,
        )


class AwoxColorCluster(CustomCluster, Color):
    """AwoX Custom Color Cluster for processing manufacturer specific commands."""

    class ServerCommandDefs(Color.ServerCommandDefs):
        """Server command definitions."""

        awox_color = ZCLCommandDef(
            id=0x30,
            schema={
                "param1": t.uint8_t,
                "color_byte": t.uint8_t,
                "param3": t.uint8_t,
                "param4": t.uint8_t,
            },
            is_manufacturer_specific=False,
        )


class Awox33952Remote(CustomDevice):
    """AwoX 33952 Remote controller."""

    signature = {
        MODELS_INFO: [("AwoX", "TLSR82xx"), ("AwoX", "ERCU_Zm")],
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 260,
                DEVICE_TYPE: 2048,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    AwoxLevelControlCluster,
                    AwoxColorCluster,
                    LightLink.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: 4751,
                DEVICE_TYPE: 2048,
                INPUT_CLUSTERS: [AWOX_CLUSTER_ID_1, AWOX_CLUSTER_ID_2],
                OUTPUT_CLUSTERS: [AWOX_CLUSTER_ID_1, AWOX_CLUSTER_ID_2],
            },
        },
    }

    device_automation_triggers = {
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
        ("step", "up"): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        ("step", "down"): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        ("step_with_on_off", "up"): {
            COMMAND: "step_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        ("step_with_on_off", "down"): {
            COMMAND: "step_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        ("move", "up"): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        ("move", "down"): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        ("move_with_on_off", "up"): {
            COMMAND: "move_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        ("move_with_on_off", "down"): {
            COMMAND: "move_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        ("stop", ""): {
            COMMAND: COMMAND_STOP,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
        },
        ("stop_with_on_off", ""): {
            COMMAND: "stop_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
        },
        ("press", "refresh"): {
            COMMAND: "awox_refresh",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
        },
        ("press", "color_red"): {
            COMMAND: "awox_color",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"color_byte": 0xD0},
        },
        ("press", "color_yellow"): {
            COMMAND: "awox_color",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"color_byte": 0xD2},
        },
        ("press", "color_green"): {
            COMMAND: "awox_color",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"color_byte": 0xD4},
        },
        ("press", "color_blue"): {
            COMMAND: "awox_color",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"color_byte": 0xD6},
        },
        ("step_color_temp", "up"): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        ("step_color_temp", "down"): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 3},
        },
        ("move_hue", "refresh_colored"): {
            COMMAND: "move_hue",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1, "rate": 12},
        },
        ("move_enhanced_hue", "light_movement"): {
            COMMAND: "enhanced_move_hue",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
        },
        ("recall", "scene_1"): {
            COMMAND: "recall",
            CLUSTER_ID: Scenes.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"scene_id": 1},
        },
        ("recall", "scene_2"): {
            COMMAND: "recall",
            CLUSTER_ID: Scenes.cluster_id,
            ENDPOINT_ID: 1,
            PARAMS: {"scene_id": 2},
        },
    }
