"""Third Reality curtain devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityCurtainCluster(CustomCluster):
    """Third Reality's curtain private cluster."""

    cluster_id = 0xFFF1

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        enable_disable_pir_remote: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        
        allow_bind: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSB015BZ")
    .replaces(ThirdRealityCurtainCluster)
    .switch(
        attribute_name=ThirdRealityCurtainCluster.AttributeDefs.enable_disable_pir_remote.name,
        cluster_id=ThirdRealityCurtainCluster.cluster_id,
        force_inverted=True,
        translation_key="enable_disable_pir_mode",
        fallback_name="Enable/Disable PIR Remote",
    )
    .write_attr_button(
        attribute_name=ThirdRealityCurtainCluster.AttributeDefs.allow_bind.name,
        attribute_value=0x01,
        cluster_id=ThirdRealityCurtainCluster.cluster_id,
        translation_key="allow_bind",
        fallback_name="Allow bind",
        endpoint_id=1,
    )
    .add_to_registry()
)
