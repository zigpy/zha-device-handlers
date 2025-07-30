"""Texas Instruments Z-Stack router device."""

from typing import Final

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
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


(
    QuirkBuilder("TexasInstruments", "ti.router")
    .replaces(replacement_cluster_class=BasicCluster, cluster_id=Basic.cluster_id, endpoint_id=8)
    .replaces(replacement_cluster_class=BasicCluster, cluster_id=Basic.cluster_id, endpoint_id=8, cluster_type="output")
    .add_to_registry()
)
