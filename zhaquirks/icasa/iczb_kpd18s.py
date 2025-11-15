"""icasa KPD18S device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_RECALL,
    COMMAND_STOP,
    COMMAND_STORE,
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

(
    QuirkBuilder("icasa", "ICZB-KPD18S")
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 6,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 8,
                PARAMS: {"move_mode": 0, "rate": 50},
            },
            (LONG_RELEASE, BUTTON): {
                COMMAND: COMMAND_STOP,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 8,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 6,
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 8,
                PARAMS: {"move_mode": 1, "rate": 50},
            },
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_RECALL,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 1},
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_RECALL,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 2},
            },
            (SHORT_PRESS, BUTTON_3): {
                COMMAND: COMMAND_RECALL,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 3},
            },
            (SHORT_PRESS, BUTTON_4): {
                COMMAND: COMMAND_RECALL,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 4},
            },
            (SHORT_PRESS, BUTTON_5): {
                COMMAND: COMMAND_RECALL,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 5},
            },
            (SHORT_PRESS, BUTTON_6): {
                COMMAND: COMMAND_RECALL,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 6},
            },
            (LONG_PRESS, BUTTON_1): {
                COMMAND: COMMAND_STORE,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 1},
            },
            (LONG_PRESS, BUTTON_2): {
                COMMAND: COMMAND_STORE,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 2},
            },
            (LONG_PRESS, BUTTON_3): {
                COMMAND: COMMAND_STORE,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 3},
            },
            (LONG_PRESS, BUTTON_4): {
                COMMAND: COMMAND_STORE,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 4},
            },
            (LONG_PRESS, BUTTON_5): {
                COMMAND: COMMAND_STORE,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 5},
            },
            (LONG_PRESS, BUTTON_6): {
                COMMAND: COMMAND_STORE,
                ENDPOINT_ID: 1,
                CLUSTER_ID: 5,
                PARAMS: {"group_id": 0, "scene_id": 6},
            },
        }
    )
    .add_to_registry()
)
