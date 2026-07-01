"""Third Reality plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityPlugCluster(CustomCluster):
    """Third Reality's plug private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        reset_summation_delivered: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSP02028BZ")
    .also_applies_to("Third Reality, Inc", "3RSPE01044BZ")
    .replaces(ThirdRealityPlugCluster)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_summation_delivered.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        translation_key="reset_summation_delivered",
        fallback_name="Reset summation delivered",
    )
    .add_to_registry()
)
