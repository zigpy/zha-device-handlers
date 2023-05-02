"""Module for Legrand switches (without dimming functionality)."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID, LegrandCluster


class SwitchWithNeutral(CustomDevice):
    """Light switch with neutral wire."""

    signature = {
        # {
        #     "endpoints": {
        #         "1": {
        #         "profile_id": 260,
        #         "device_type": "0x0100",
        #         "in_clusters": [
        #             "0x0000",
        #             "0x0003",
        #             "0x0004",
        #             "0x0005",
        #             "0x0006",
        #             "0x000f",
        #             "0xfc01"
        #         ],
        #         "out_clusters": [
        #             "0x0000",
        #             "0x0019",
        #             "0xfc01"
        #         ]
        #         }
        #     },
        #     "manufacturer": " Legrand",
        #     "model": " Light switch with neutral",
        # }
        MODELS_INFO: [(f" {LEGRAND}", " Light switch with neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Ota.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    BinaryInput.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Ota.cluster_id,
                    LegrandCluster,
                ],
            }
        }
    }
