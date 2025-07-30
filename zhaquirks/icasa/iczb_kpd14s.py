"""icasa KPD14S device."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_RECALL,
    COMMAND_STOP,
    COMMAND_STORE,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)


(
    QuirkBuilder("icasa", "ICZB-KPD14S")
    .device_automation_triggers({
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
    })
    .add_to_registry()
)
