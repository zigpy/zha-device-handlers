"""Device handler for Insta NEXENTRO Pushbutton Interface."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic, Identify, Groups, Scenes, OnOff, LevelControl, Ota, GreenPowerProxy
from zigpy.zcl.clusters.lighting import Color

from zhaquirks import MODELS_INFO, ENDPOINTS, PROFILE_ID, DEVICE_TYPE, INPUT_CLUSTERS, OUTPUT_CLUSTERS
from zhaquirks.const import SHORT_PRESS, TURN_ON, COMMAND, COMMAND_ON, TURN_OFF, COMMAND_OFF, COMMAND_TOGGLE, BUTTON, \
    OPEN, CLOSE, COMMAND_MOVE_ON_OFF, DIM_UP, COMMAND_MOVE, DIM_DOWN, COMMAND_STOP, STOP, ENDPOINT_ID, ALT_SHORT_PRESS
from zhaquirks.insta import INSTA

COMMAND_OPEN = "up_open"
COMMAND_CLOSE = "down_close"
COMMAND_STORE = "store"
COMMAND_RECALL = "recall"


class InstaNexentroPushbuttonInterface(CustomDevice):
    signature = {
        MODELS_INFO: [(INSTA, "NEXENTRO Pushbutton Interface")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=4 profile=260 device_type=261
            # device_version=1
            # input_clusters=[0, 3]
            # output_clusters=[3, 4, 5, 6, 8, 25, 768]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=5 profile=260 device_type=261
            # device_version=1
            # input_clusters=[0, 3]
            # output_clusters=[3, 4, 5, 6, 8, 25, 768]>
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=7 profile=260 device_type=515
            # device_version=1
            # input_clusters=[0, 3]
            # output_clusters=[3, 4, 25, 258]>
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=1
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [
                ],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id
                ],
            }
        }
    }

    replacement = {
        ENDPOINTS: {
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [
                ],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, ENDPOINT_ID: 4},
        (ALT_SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON, ENDPOINT_ID: 5},
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 4},
        (ALT_SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 5},
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 4},
        (ALT_SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 5},
        (SHORT_PRESS, OPEN): {COMMAND: COMMAND_OPEN},
        (SHORT_PRESS, CLOSE): {COMMAND: COMMAND_CLOSE},
        (SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_MOVE_ON_OFF, ENDPOINT_ID: 4},
        (ALT_SHORT_PRESS, DIM_UP): {COMMAND: COMMAND_MOVE_ON_OFF, ENDPOINT_ID: 5},
        (SHORT_PRESS, DIM_DOWN): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 4},
        (ALT_SHORT_PRESS, DIM_DOWN): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 5},
        (SHORT_PRESS, STOP): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 4},
        (ALT_SHORT_PRESS, STOP): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 5},
    }
