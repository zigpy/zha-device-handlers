"""Third Reality radar sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityRadarCluster(CustomCluster):
    """Third Reality's radar sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        detection_interval: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSMR01067Z")
    .replaces(ThirdRealityRadarCluster)
    .number(
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.detection_interval.name,
        min_value=0,
        max_value=3600,
        unit=UnitOfTime.SECONDS,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        translation_key="detection_interval",
        fallback_name="Detection interval",
    )
    .add_to_registry()
)
