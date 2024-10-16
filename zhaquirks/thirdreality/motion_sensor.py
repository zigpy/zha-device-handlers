"""Third Reality Plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityMotionCluster(CustomCluster):
    """Third Reality's motion sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        cooldown_time: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
            name="Cooldown_Time",
        )


(
    QuirkBuilder("Third Reality, Inc", "3RMS16BZ")
    .replaces(ThirdRealityMotionCluster)
    .number(
        attribute_name=ThirdRealityMotionCluster.AttributeDefs.cooldown_time.name,
        min_value=5,
        max_value=3600,
        cluster_id=ThirdRealityMotionCluster.cluster_id,
    )
    .add_to_registry()
)
