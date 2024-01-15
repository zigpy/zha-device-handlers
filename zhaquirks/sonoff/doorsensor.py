"""
Handle Doorsensor not correctly implementing certain clusters
"""

from zigpy.quirks import CustomDevice

import zigpy.profiles.zha as zha_p

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zigpy.zcl.clusters.security import IasZone

from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)


class DS01DoorSensor(CustomDevice):
    """DoorSensor from Sonoff"""
    signature = {
        MODELS_INFO: [
            ("zbeacon", "DS01")
        ],

        ENDPOINTS: {
            # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=1026, device_version=0, input_clusters=[0, 3, 1, 1280, 32], output_clusters=[25])
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id
                ]
            }
        }
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    PowerConfiguration,
                    Identify,
                    IasZone
                ],
                OUTPUT_CLUSTERS: [
                    Ota,
                ],
            }
        }
    }