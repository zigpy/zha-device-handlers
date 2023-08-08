"""Third Reality vibrate devices."""
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration
from zhaquirks import CustomCluster
from zigpy.zcl.clusters.security import IasZone
import zigpy.types as t

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFFF1

class ThirdRealityAccelCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    attributes = {
        0x0001: ("x_axis", t.int16s, True),
        0x0002: ("y_axis", t.int16s, True),
        0x0003: ("z_axis", t.int16s, True),
    }

class Vibrate(CustomDevice):
    """thirdreality vibrate device - alternate version."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RVS01031Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityAccelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityAccelCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }