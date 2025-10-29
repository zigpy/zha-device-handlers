"""Third Reality garage door lite sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityGarageCluster(CustomCluster):
    """Third Reality's garage door lite private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        open_delay_time: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

        z_axis_calibration: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RDTS01056Z")
    .replaces(ThirdRealityGarageCluster)
    .number(
        attribute_name=ThirdRealityGarageCluster.AttributeDefs.open_delay_time.name,
        cluster_id=ThirdRealityGarageCluster.cluster_id,
        min_value=0,
        max_value=3600,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="open_delay_time",
        fallback_name="Open delay time",
    )
    .write_attr_button(
        attribute_name=ThirdRealityGarageCluster.AttributeDefs.z_axis_calibration.name,
        cluster_id=ThirdRealityGarageCluster.cluster_id,
        attribute_value=0x01,
        translation_key="calibrate_z_axis",
        fallback_name="Calibrate Z axis",
    )
    .add_to_registry()
)
