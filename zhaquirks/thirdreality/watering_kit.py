"""Third Reality water leak devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityWateringKitCluster(CustomCluster):
    """Third Reality's water leak sensor private cluster."""

    cluster_id = 0xFFF2

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        water_duration: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        water_interval: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RWK0148Z")
    .replaces(ThirdRealityWateringKitCluster)
    .number(
        attribute_name=ThirdRealityWateringKitCluster.AttributeDefs.water_duration.name,
        min_value=1,
        max_value=1800,
        step=1,
        unit=UnitOfTime.SECONDS,
        cluster_id=ThirdRealityWateringKitCluster.cluster_id,
        translation_key="water_duration",
        fallback_name="Water Duration",
    )
    .number(
        attribute_name=ThirdRealityWateringKitCluster.AttributeDefs.water_interval.name,
        min_value=0,
        max_value=30,
        step=1,
        unit=UnitOfTime.DAYS,
        cluster_id=ThirdRealityWateringKitCluster.cluster_id,
        translation_key="water_interval",
        fallback_name="Water Interval",
    )
    .add_to_registry()
)
