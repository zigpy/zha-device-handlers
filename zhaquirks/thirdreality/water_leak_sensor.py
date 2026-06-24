"""Third Reality water leak devices."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster


class ThirdRealityWaterLeakCluster(CustomCluster):
    """Third Reality's water leak sensor private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        enable_siren: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        siren_time: Final = ZCLAttributeDef(
            id=0x0011,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RWS18BZ")
    .replaces(ThirdRealityWaterLeakCluster)
    .switch(
        attribute_name=ThirdRealityWaterLeakCluster.AttributeDefs.enable_siren.name,
        cluster_id=ThirdRealityWaterLeakCluster.cluster_id,
        translation_key="enable_siren",
        fallback_name="Enable siren",
    )
    .number(
        attribute_name=ThirdRealityWaterLeakCluster.AttributeDefs.siren_time.name,
        min_value=0,
        max_value=255,
        unit=UnitOfTime.MINUTES,
        cluster_id=ThirdRealityWaterLeakCluster.cluster_id,
        translation_key="siren_time",
        fallback_name="Siren time",
    )
    .add_to_registry()
)
