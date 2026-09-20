"""Third Reality light devices."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


class ThirdRealityLightCluster(CustomCluster):
    """Third Reality's light private cluster."""

    cluster_id = 0xFF04

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        allow_bind: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RCB02070Z")
    .applies_to("Third Reality, Inc", "3RCB01057Z")
    .applies_to("Third Reality, Inc", "3RCB1095Z")
    .replaces(ThirdRealityLightCluster, endpoint_id=1)
    .write_attr_button(
        attribute_name=ThirdRealityLightCluster.AttributeDefs.allow_bind.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityLightCluster.cluster_id,
        translation_key="allow_remote_binding",
        fallback_name="Allow remote binding",
    )
    .add_to_registry()
)
