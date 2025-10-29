"""Third Reality Switch Gen2 devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealitySwitchCluster(CustomCluster):
    """Third Reality's Switch private cluster."""

    cluster_id = 0xFF02

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        on_to_off_delay: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        off_to_on_delay: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSS009Z")
    .replaces(ThirdRealitySwitchCluster)
    .number(
        attribute_name=ThirdRealitySwitchCluster.AttributeDefs.on_to_off_delay.name,
        cluster_id=ThirdRealitySwitchCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="turn_off_delay",
        fallback_name="Turn off delay",
    )
    .number(
        attribute_name=ThirdRealitySwitchCluster.AttributeDefs.off_to_on_delay.name,
        cluster_id=ThirdRealitySwitchCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="turn_on_delay",
        fallback_name="Turn on delay",
    )
    .add_to_registry()
)
