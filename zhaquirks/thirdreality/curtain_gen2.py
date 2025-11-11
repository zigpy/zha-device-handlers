"""Third Reality Blind Gen2 devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class THIRD_REALITY_Blind_Gen2_CLUSTER(CustomCluster):
    """Third Reality's Blind Gen2 private cluster."""

    cluster_id = 0xFFF1

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        enable_disable_pir_remote: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        compensation_speed: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.int8s,
            is_manufacturer_specific=True,
        )

        limit_position: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSB02015Z")
    .replaces(THIRD_REALITY_Blind_Gen2_CLUSTER, endpoint_id=1)
    .switch(
        attribute_name=THIRD_REALITY_Blind_Gen2_CLUSTER.AttributeDefs.enable_disable_pir_remote.name,
        cluster_id=THIRD_REALITY_Blind_Gen2_CLUSTER.cluster_id,
        force_inverted=True,
        translation_key="enable_pir_mode",
        fallback_name="Enable PIR remote",
    )
    .number(
        attribute_name=THIRD_REALITY_Blind_Gen2_CLUSTER.AttributeDefs.compensation_speed.name,
        cluster_id=THIRD_REALITY_Blind_Gen2_CLUSTER.cluster_id,
        endpoint_id=1,
        min_value=-100,
        max_value=100,
        step=1,
        mode="box",
        translation_key="compensation_speed",
        fallback_name="Compensation speed",
    )
    .number(
        attribute_name=THIRD_REALITY_Blind_Gen2_CLUSTER.AttributeDefs.limit_position.name,
        cluster_id=THIRD_REALITY_Blind_Gen2_CLUSTER.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=3800,
        step=1,
        translation_key="limit_position",
        fallback_name="Limit position",
    )
    .add_to_registry()
)
