"""Device handler for IKEA of Sweden TRADFRI remote control."""
from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
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
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    COMMAND_STEP,
    COMMAND_STEP_ON_OFF,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, LightLinkCluster, ScenesCluster


class IkeaTradfriRemote(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49246 device_type=2096
        # device_version=2
        # input_clusters=[0, 1, 3, 9, 2821, 4096]
        # output_clusters=[3, 4, 5, 6, 8, 25, 4096]>
        MODELS_INFO: [(IKEA, "TRADFRI remote control")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Diagnostic.cluster_id,
                    LightLinkCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ScenesCluster,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
        },
        (LONG_PRESS, TURN_ON): {
            COMMAND: COMMAND_RELEASE,
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            PARAMS: {"param1": 0},
        },
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        (SHORT_PRESS, LEFT): {
            COMMAND: COMMAND_PRESS,
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            PARAMS: {
                "param1": 257,
                "param2": 13,
                "param3": 0,
            },
        },
        (LONG_PRESS, LEFT): {
            COMMAND: COMMAND_HOLD,
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            PARAMS: {
                "param1": 3329,
                "param2": 0,
            },
        },
        (SHORT_PRESS, RIGHT): {
            COMMAND: COMMAND_PRESS,
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            PARAMS: {
                "param1": 256,
                "param2": 13,
                "param3": 0,
            },
        },
        (LONG_PRESS, RIGHT): {
            COMMAND: COMMAND_HOLD,
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
            PARAMS: {
                "param1": 3328,
                "param2": 0,
            },
        },
    }
