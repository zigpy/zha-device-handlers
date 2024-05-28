"""Third Reality Plug devices."""

from typing import Final

from zigpy.quirks.v2 import ClusterType, add_to_registry_v2
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.thirdreality import THIRD_REALITY


class ThirdRealityPlugCluster(CustomCluster):
    """The private cluster id of Third Reality's PLUG."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Attribute of private cluster id."""

        reset_summation_delivered: Final = ZCLAttributeDef(
            id=0x0000,
            name="reset_summation_delivered",
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    add_to_registry_v2(THIRD_REALITY, "3RSP02028BZ")
    .adds(ThirdRealityPlugCluster)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_summation_delivered.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        translation_key="reset_summation_delivered"
    )
)

(
    add_to_registry_v2(THIRD_REALITY, "3RSPE01044BZ")
    .adds(ThirdRealityPlugCluster)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_summation_delivered.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        translation_key="reset_summation_delivered"
    )
)
