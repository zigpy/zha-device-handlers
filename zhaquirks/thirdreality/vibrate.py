"""Third Reality vibrate devices."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone
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

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFFF1


class ThirdRealityAccelCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        x_axis: Final = ZCLAttributeDef(
            id=0x0001, type=t.int16s, is_manufacturer_specific=True
        )
        y_axis: Final = ZCLAttributeDef(
            id=0x0002, type=t.int16s, is_manufacturer_specific=True
        )
        z_axis: Final = ZCLAttributeDef(
            id=0x0003, type=t.int16s, is_manufacturer_specific=True
        )


(
    QuirkBuilder(THIRD_REALITY, "3RVS01031Z")
    .replaces(replacement_cluster_class=ThirdRealityAccelCluster, cluster_id=MANUFACTURER_SPECIFIC_CLUSTER_ID)
    .add_to_registry()
)
