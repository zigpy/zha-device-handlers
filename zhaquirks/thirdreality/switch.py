"""Third Reality switch devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealitySwitchCluster(CustomCluster):
    """Third Reality's temperature and humidity sensor private cluster."""

    cluster_id = 0xFF02

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        count_down_time: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSS009Z")
    .replaces(ThirdRealitySwitchCluster)
    .number(
        attribute_name=ThirdRealitySwitchCluster.AttributeDefs.count_down_time.name,
        min_value=0,
        max_value=65535,
        step=1,
        unit=UnitOfTime.SECONDS,
        cluster_id=ThirdRealitySwitchCluster.cluster_id,
        translation_key="count_down_time",
        fallback_name="Count Down Time",
    )
    .add_to_registry()
)
