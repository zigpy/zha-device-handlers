"""Profalux device"""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
    Time,
    Commissioning,
)

from zigpy.zcl.clusters.closures import Shade

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    DOUBLE_PRESS,
    TURN_ON,
    TURN_OFF,
    COMMAND,
    COMMAND_ON,
    COMMAND_OFF,
    COMMAND_STOP,
    COMMAND_TOGGLE,
    CLUSTER_ID,
    ENDPOINT_ID,
    DEVICE_VERSION,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
)

from . import (
    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
    PROFALUX_MANUFACTURER,
    PROFALUX_MODEL_COVER,
)


class ProfaluxCover(CustomDevice):
    """Profalux covers"""

    signature = {
        # <SimpleDescriptor
        #     endpoint=1 profile=260 device_type=512 device_version=0
        #     input_clusters=[0, 3, 4, 5, 6, 8, 10, 21, 256, 64544, 64545]
        #     output_clusters=[3, 64544]
        # >
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID, # profile = 260 - 0x104
                DEVICE_TYPE: zha.DeviceType.SHADE, # device_type = 512 - 0x200
                DEVICE_VERSION: 0x00, # device_version = 0
                INPUT_CLUSTERS: [
                    Basic.cluster_id, # 0
                    Identify.cluster_id, # 3
                    Groups.cluster_id, # 4
                    Scenes.cluster_id, # 5
                    OnOff.cluster_id, # 6
                    LevelControl.cluster_id, # 8
                    Time.cluster_id, # 10
                    Commissioning.cluster_id, # 21
                    Shade.cluster_id, # 256
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1, # 64544
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2, # 64545
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1, # 64544
                ],
            },
        }
    }

    replacement = {
        DEVICE_MANUFACTURER: PROFALUX_MANUFACTURER,
        DEVICE_MODEL: PROFALUX_MODEL_COVER,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID, # profile = 260 - 0x104
                DEVICE_TYPE: zha.DeviceType.SHADE, # device_type = 512 - 0x200 
                DEVICE_VERSION: 0x00, # device_version = 0
                INPUT_CLUSTERS: [
                    Basic.cluster_id, # 0
                    Identify.cluster_id, # 3
                    Groups.cluster_id, # 4
                    Scenes.cluster_id, # 5
                    OnOff.cluster_id, # 6
                    LevelControl.cluster_id, # 8
                    Time.cluster_id, # 10
                    Commissioning.cluster_id, # 21
                    Shade.cluster_id, # 256
                    #MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                    #MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    #MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                ],
            },
        }
    }
    """
    device_automation_triggers = {
        (DOUBLE_PRESS, COMMAND_TOGGLE): {COMMAND: COMMAND_TOGGLE, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (SHORT_PRESS, COMMAND_STOP): {COMMAND: COMMAND_STOP, CLUSTER_ID: 8, ENDPOINT_ID: 1},
    }
    """