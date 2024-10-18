"""Third Reality Plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityWaterLeakCluster(CustomCluster):
    """Third Reality's water leak sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        enable_siren: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint8_t,
            is_manufacturer_specific=True,
            name="Enable_or_Disable_siren",
        )

        siren_time: Final = ZCLAttributeDef(
            id=0x0011,
            type=t.uint8_t,
            is_manufacturer_specific=True,
            name="Siren_timer",
        )


(
    QuirkBuilder("Third Reality, Inc", "3RWS18BZ")
    .replaces(ThirdRealityWaterLeakCluster)
    .switch(
        attribute_name=ThirdRealityWaterLeakCluster.AttributeDefs.enable_siren.name,
        cluster_id=ThirdRealityWaterLeakCluster.cluster_id,
    )
    .number(
        attribute_name=ThirdRealityWaterLeakCluster.AttributeDefs.siren_time.name,
        min_value=0,
        max_value=255,
        cluster_id=ThirdRealityWaterLeakCluster.cluster_id,
    )
    .add_to_registry()
)
