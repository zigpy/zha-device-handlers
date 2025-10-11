"""Third Reality garage door lite sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import PollControl
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.quirks.v2.homeassistant import UnitOfTime, NumberDeviceClass


class ThirdRealityGarageCluster(CustomCluster):
    """Third Reality's garage door lite private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        undetected_to_detected_delay: Final = ZCLAttributeDef(
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
    .removes(PollControl.cluster_id)
    .number(
        attribute_name=ThirdRealityGarageCluster.AttributeDefs.undetected_to_detected_delay.name,
        cluster_id=ThirdRealityGarageCluster.cluster_id,
        min_value=0,
        max_value=3600,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="undetected_to_detected_delay",
        fallback_name="Undetected to detected delay",
    )
    .write_attr_button(
        attribute_name=ThirdRealityGarageCluster.AttributeDefs.z_axis_calibration.name,
        cluster_id=ThirdRealityGarageCluster.cluster_id,
		attribute_value=0x01,
		translation_key="enable_z_axis_calibration",
        fallback_name="Enable Z axis calibration",
    )
    .add_to_registry()
)
