"""Third Reality Blind Gen2 devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.quirks.v2.homeassistant import UnitOfTime



class THIRD_REALITY_Switch_CLUSTER(CustomCluster):
    """Third Reality's Switch private cluster."""

    cluster_id = 0xFF02

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""
		
        
        on_to_off_delay: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
          
        off_to_on_delay: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSS009Z")
    .replaces(THIRD_REALITY_Switch_CLUSTER)
    .number(
        attribute_name=THIRD_REALITY_Switch_CLUSTER.AttributeDefs.on_to_off_delay.name,
        cluster_id=THIRD_REALITY_Switch_CLUSTER.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        unit=UnitOfTime.SECONDS,
        step=1,
        translation_key="on_to_off_delay",
        fallback_name="on_to_off_delay",
    )
    .number(
        attribute_name=THIRD_REALITY_Switch_CLUSTER.AttributeDefs.off_to_on_delay.name,
        cluster_id=THIRD_REALITY_Switch_CLUSTER.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        unit=UnitOfTime.SECONDS,
        step=1,
        translation_key="off_to_on_delay",
        fallback_name="off_to_on_delay",
    )
    .add_to_registry()
)
