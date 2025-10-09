"""Third Reality door sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityDoorCluster(CustomCluster):
    """Third Reality's door sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        open_delay_time: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RDS17BZ")
    .replaces(ThirdRealityDoorCluster)
    .number(
        attribute_name=ThirdRealityDoorCluster.AttributeDefs.open_delay_time.name,
        min_value=0,
        max_value=3600,
        unit=UnitOfTime.SECONDS,
        cluster_id=ThirdRealityDoorCluster.cluster_id,
        translation_key="open_delay_time",
        fallback_name="Open Delay Time",
    )
    .add_to_registry()
)
