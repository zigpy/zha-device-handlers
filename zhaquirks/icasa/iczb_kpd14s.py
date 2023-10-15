"""icasa KPD14S device."""
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
    ARGS,
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
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
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

COMMAND_STORE = "store"
COMMAND_RECALL = "recall"


class IcasaKPD14S(CustomDevice):
    """icasa KPD14S device (looks like a white label Sunricher)."""

    signature = {
        MODELS_INFO: [("icasa", "ICZB-KPD14S")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 6,
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 8,
            ARGS: [0, 50],
        },
        (LONG_RELEASE, DIM_UP): {
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
            ARGS: [1, 50],
        },
        (LONG_RELEASE, DIM_DOWN): {
            COMMAND: COMMAND_STOP,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 8,
        },
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_RECALL,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 5,
            ARGS: [0, 1],
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_RECALL,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 5,
            ARGS: [0, 2],
        },
        (LONG_PRESS, BUTTON_1): {
            COMMAND: COMMAND_STORE,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 5,
            ARGS: [0, 1],
        },
        (LONG_PRESS, BUTTON_2): {
            COMMAND: COMMAND_STORE,
            ENDPOINT_ID: 1,
            CLUSTER_ID: 5,
            ARGS: [0, 2],
        },
    }
