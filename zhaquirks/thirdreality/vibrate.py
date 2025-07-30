"""Third Reality vibrate devices."""

from typing import Final

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
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
    .replaces(
        replacement_cluster_class=ThirdRealityAccelCluster,
        cluster_id=MANUFACTURER_SPECIFIC_CLUSTER_ID,
    )
    .add_to_registry()
)
