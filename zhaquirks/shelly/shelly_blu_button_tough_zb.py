"""ZHA Quirk for Shelly BLU Button Tough 1 ZB"""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    PowerConfiguration,
    Scenes,
)

from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    INPUT_CLUSTERS,
    LONG_PRESS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)


class ShellyBluButtonTough1(CustomDevice):
    """Shelly BLU Button Tough 1 ZB"""

    signature = {
        "models_info": [
            ("Shelly", "BLU Button Tough 1 ZB"),
        ],
        "endpoints": {
            1: {
                "profile_id": 0x0104,
                "device_type": 0x0000,
                "input_clusters": [0x0000, 0x0001, 0x0003],
                "output_clusters": [0x0003, 0x0005, 0x0006, 0x0008],
            },
            2: {
                "profile_id": 0x0104,
                "device_type": 0x0000,
                "input_clusters": [0x0000, 0x0003],
                "output_clusters": [0x0003, 0x0005, 0x0006],
            },
            3: {
                "profile_id": 0x0104,
                "device_type": 0x0000,
                "input_clusters": [0x0000, 0x0003],
                "output_clusters": [0x0003, 0x0005, 0x0006],
            },
        },
    }

    replacement = {
        "endpoints": {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [Basic, PowerConfiguration, Identify],
                OUTPUT_CLUSTERS: [Identify, Groups, Scenes, OnOff, LevelControl],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [Basic, Identify],
                OUTPUT_CLUSTERS: [Identify, Groups, Scenes, OnOff],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [Basic, Identify],
                OUTPUT_CLUSTERS: [Identify, Groups, Scenes, OnOff],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
        },
        (DOUBLE_PRESS, BUTTON): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 2,
        },
        (LONG_PRESS, BUTTON): {
            COMMAND: "recall",
            CLUSTER_ID: 5,
            ENDPOINT_ID: 1,
        },
    }
