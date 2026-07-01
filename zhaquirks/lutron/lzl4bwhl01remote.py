"""Device handler for Lutron LZL4BWHL01 Remote."""

from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import GroupBoundCluster
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    COMMAND_STEP,
    COMMAND_STEP_ON_OFF,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
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

MANUFACTURER_SPECIFIC_CLUSTER_ID_1 = 0xFF00  # decimal = 65280
MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC44  # decimal = 64580


class OnOffGroupCluster(GroupBoundCluster, OnOff):
    """On/Off Cluster which only binds to a group."""


class LevelControlGroupCluster(GroupBoundCluster, LevelControl):
    """Level Control Cluster which only binds to a group."""


class LutronLZL4BWHL01Remote(CustomDevice):
    """Custom device representing Lutron LZL4BWHL01 Remote."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2080
        #  device_version=2
        #  input_clusters=[0, 4096, 65280, 64580]
        #  output_clusters=[4096, 3, 6, 8, 4, 5, 0, 65280]>
        MODELS_INFO: [
            ("Lutron", "LZL4BWHL01 Remote"),
            (" Lutron", "LZL4BWHL01 Remote"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
                ],
                OUTPUT_CLUSTERS: [
                    LightLink.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
                ],
                OUTPUT_CLUSTERS: [
                    LightLink.cluster_id,
                    Identify.cluster_id,
                    OnOffGroupCluster,
                    LevelControlGroupCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"level": 254, "transition_time": 4},
        },
        (SHORT_PRESS, TURN_OFF): {
            COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"level": 0, "transition_time": 4},
        },
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
    }
