"""Texas Instruments Z-Stack router device."""

from typing import Final

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Identify
from zigpy.zcl.foundation import ZCLAttributeDef

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

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        transmit_power: Final = ZCLAttributeDef(
            id=0x1337, type=t.int8s, is_manufacturer_specific=True
        )


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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
