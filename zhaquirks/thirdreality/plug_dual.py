"""Third Reality dual plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityPlugCluster(CustomCluster):
    """Third Reality's dual plug private cluster."""

    cluster_id = 0xFF03

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # reset the accumulated power of the plug
        reset_summation_delivered: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        # turn off delay
        on_to_off_delay: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        # turn on delay
        off_to_on_delay: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RDP01072Z")
    .also_applies_to("Third Reality, Inc", "3RWP01073Z")
    .replaces(ThirdRealityPlugCluster, endpoint_id=1)
    .replaces(ThirdRealityPlugCluster, endpoint_id=2)  # have two endpoint
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_summation_delivered.name,
        attribute_value=0x01,  # 1 reset summation delivered
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        translation_key="reset_summation_delivered_ep1",
        fallback_name="Reset left summation delivered",  # ep1 is left
    )
    .write_attr_button(  # reset the accumulated power of the plug
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_summation_delivered.name,
        attribute_value=0x01,  # 1 reset summation delivered
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=2,
        translation_key="reset_summation_delivered_ep2",
        fallback_name="Reset right summation delivered ep2",  # ep2 is right
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.on_to_off_delay.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="on_to_off_delay_ep1",
        fallback_name="Turn off delay",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.on_to_off_delay.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="on_to_off_delay_ep2",
        fallback_name="Turn off delay",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.off_to_on_delay.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="off_to_on_delay_ep1",
        fallback_name="Turn on delay",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.off_to_on_delay.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=2,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="off_to_on_delay_ep2",
        fallback_name="Turn on delay",
    )
    .add_to_registry()
)
