"""Third Reality WaterLeak devices."""

from typing import Final
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration, OnOff
from zigpy.zcl.clusters.security import IasZone
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)

from zhaquirks.thirdreality import THIRD_REALITY
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.thirdreality import THIRD_REALITY

THIRD_REALITY_WATERLEAK_CLUSTER_ID = 0xFF01
THIRD_REALITY_WATERLEAK_BRIGHTNESS_CLUSTER_ID = 0xFF00
DELAY_OPEN_ATTR_ID = 0x0000



class ThirdRealityWaterLeakCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_WATERLEAK_CLUSTER_ID

    attributes = {
        0x0010:("siren_on_off", t.uint8_t, True),
        0x0011:("siren_mintues", t.uint8_t, True),
    }

class ThirdRealityWaterLeakBrightnessCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_WATERLEAK_BRIGHTNESS_CLUSTER_ID

    attributes = {
        0x0000: ("redlight", t.uint8_t, False),
        0x0002: ("bluelight", t.uint8_t, False),
    }


class WaterLeak(CustomDevice):
    """ThirdReality WaterLeak device."""

    signature = {
        MODELS_INFO: [
            (THIRD_REALITY, "3RWS18BZ"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityWaterLeakCluster.cluster_id,  # 0xFF01
                    ThirdRealityWaterLeakBrightnessCluster.cluster_id,   #0xFF00
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                    OnOff.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,    
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityWaterLeakCluster,  # 0xFF01
                    ThirdRealityWaterLeakBrightnessCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                    OnOff.cluster_id,
                ],
            },
        },
    }
