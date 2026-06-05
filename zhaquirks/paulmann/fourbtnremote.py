"""Device handler for Paulmann 4-button remote control."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP_ON_OFF,
    DEVICE_TYPE,
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
)
from zhaquirks.paulmann import PAULMANN, PAULMANN_VARIANT


class PaulmannRemote4Btn(CustomDevice):
    """Custom device representing Paulmann 4-button 501.34 remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1
        # device_version=0
        # input_clusters=[0, 1, 3, 2821, 4096]
        # output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
        MODELS_INFO: [(PAULMANN, "501.34"), (PAULMANN_VARIANT, "501.34")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Diagnostic.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Color.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Diagnostic.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Color.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Scenes.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Diagnostic.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Color.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            2: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Diagnostic.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Color.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Scenes.cluster_id,
                ],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_1): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0, "rate": 50},
        },
        (LONG_RELEASE, BUTTON_1): {
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_2): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1, "rate": 50},
        },
        (LONG_RELEASE, BUTTON_2): {
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 2,
        },
        (LONG_PRESS, BUTTON_3): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
            PARAMS: {"move_mode": 0, "rate": 50},
        },
        (LONG_RELEASE, BUTTON_3): {
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
        },
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 2,
        },
        (LONG_PRESS, BUTTON_4): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
            PARAMS: {"move_mode": 1, "rate": 50},
        },
        (LONG_RELEASE, BUTTON_4): {
            COMMAND: COMMAND_STOP_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
        },
    }
