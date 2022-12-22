"""Texas Instruments Z-Stack router device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Identify

from zhaquirks import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class BasicCluster(CustomCluster, Basic):
    """Texas Instruments Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes[0x1337] = ("transmit_power", t.int8s, False)


class TiRouter(CustomDevice):
    """Texas Instruments Z-Stack router device."""

    signature = {
        MODELS_INFO: [("TexasInstruments", "ti.router")],
        ENDPOINTS: {
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x00FF,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x00FF,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
