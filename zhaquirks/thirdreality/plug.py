"""Third Reality plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityPlugCluster(CustomCluster):
    """Third Reality's plug private cluster."""

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
    QuirkBuilder("Third Reality, Inc", "3RSP02028BZ")
    .also_applies_to("Third Reality, Inc", "3RSPE01044BZ")
    .also_applies_to("Third Reality, Inc", "3RSPU01080Z")
    .also_applies_to("Third Reality, Inc", "3RSP02064Z")
    .also_applies_to("Third Reality, Inc", "3RSPE02065Z")
    .replaces(ThirdRealityPlugCluster)
    .write_attr_button(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.reset_summation_delivered.name,
        attribute_value=0x01,  # 1 reset summation delivered
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        translation_key="reset_summation_delivered",
        fallback_name="Reset summation delivered",
    )
    .number(
        attribute_name=ThirdRealityPlugCluster.AttributeDefs.on_to_off_delay.name,
        cluster_id=ThirdRealityPlugCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="on_to_off_delay",
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
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="off_to_on_delay",
        fallback_name="Turn on delay",
    )
    .add_to_registry()
)
