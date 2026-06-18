"""Third Reality motion sensor devices."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster


class ThirdRealityMotionCluster(CustomCluster):
    """Third Reality's motion sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        detection_interval: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RMS16BZ")
    .replaces(ThirdRealityMotionCluster)
    .number(
        attribute_name=ThirdRealityMotionCluster.AttributeDefs.detection_interval.name,
        min_value=5,
        max_value=3600,
        unit=UnitOfTime.SECONDS,
        cluster_id=ThirdRealityMotionCluster.cluster_id,
        translation_key="detection_interval",
        fallback_name="Detection interval",
    )
    .add_to_registry()
)
