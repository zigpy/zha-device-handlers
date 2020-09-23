"""Profalux device"""
from zigpy.profiles.zha import DeviceType
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
    DEVICE_VERSION,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
)

from . import (
    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
    PROFALUX_MANUFACTURER,
    PROFALUX_MODEL_REMOTE,
)


class ProfaluxRemote(CustomDevice):
    """Profalux remotes"""

    signature = {
        # <SimpleDescriptor
        #     endpoint=1 profile=260 device_type=513 device_version=0
        #     input_clusters=[0, 3, 21]
        #     output_clusters=[3, 4, 5, 6, 8, 256, 64544, 64545]
        # >
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104, # profile = 260 - 0x104
                DEVICE_TYPE: DeviceType.SHADE_CONTROLLER, # device_type = 513 - 0x201
                DEVICE_VERSION: 0x00, # device_version = 0
                INPUT_CLUSTERS: [
                    Basic.cluster_id, # 0
                    Identify.cluster_id, # 3
                    Commissioning.cluster_id, # 21
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id, # 3
                    Groups.cluster_id, # 4
                    Scenes.cluster_id, # 5
                    OnOff.cluster_id, # 6
                    LevelControl.cluster_id, # 8
                    Shade.cluster_id, # 256
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1, # 64544
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2, # 64545
                ],
            },
        }
    }

    replacement = {
        DEVICE_MANUFACTURER: PROFALUX_MANUFACTURER,
        DEVICE_MODEL: PROFALUX_MODEL_REMOTE,
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104, # profile = 260 - 0x104
                DEVICE_TYPE: DeviceType.SHADE_CONTROLLER, # device_type = 512 - 0x200 
                DEVICE_VERSION: 0x00, # device_version = 0
                INPUT_CLUSTERS: [
                    Basic.cluster_id, # 0
                    Identify.cluster_id, # 3
                    Commissioning.cluster_id, # 21
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id, # 3
                    Groups.cluster_id, # 4
                    Scenes.cluster_id, # 5
                    OnOff.cluster_id, # 6
                    LevelControl.cluster_id, # 8
                    Shade.cluster_id, # 256
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1, # 64544
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2, # 64545
                ],
            },
        }
    }