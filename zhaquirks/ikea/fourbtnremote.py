"""Device handler for IKEA of Sweden TRADFRI remote control."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    COMMAND_STOP_ON_OFF,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import (
    IKEA,
    WWAH_CLUSTER_ID,
    PowerConfiguration2AAACluster,
    ScenesCluster,
)


class IkeaTradfriRemote(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2080
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 4096, 64599]
        # output_clusters=[3, 6, 8, 25, 4096]>
        MODELS_INFO: [(IKEA, "Remote Control N2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration2AAACluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
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
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        (LONG_RELEASE, DIM_UP): {
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        (LONG_RELEASE, DIM_DOWN): {
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
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
