"""Third Reality watering kit devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityWateringKitCluster(CustomCluster):
    """Third Reality's watering kit private cluster."""

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
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        cluster_id=ThirdRealityWateringKitCluster.cluster_id,
        translation_key="water_duration",
        fallback_name="Water duration",
    )
    .number(
        attribute_name=ThirdRealityWateringKitCluster.AttributeDefs.water_interval.name,
        min_value=0,
        max_value=30,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.DAYS,
        cluster_id=ThirdRealityWateringKitCluster.cluster_id,
        translation_key="water_interval",
        fallback_name="Water interval",
    )
    .add_to_registry()
)
