"""Third Reality 24G radar sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdReality24GRadarCluster(CustomCluster):
    """Third Reality's 24G radar private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        sensor_calibration: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        sensor_sensitivity: Final = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RPS01083Z")
    .replaces(ThirdReality24GRadarCluster)
    .write_attr_button(
        attribute_name=ThirdReality24GRadarCluster.AttributeDefs.sensor_calibration.name,
        attribute_value=0x01,  # 1 sensor calibration
        cluster_id=ThirdReality24GRadarCluster.cluster_id,
        translation_key="calibrate_sensor",
        fallback_name="Calibrate sensor",
    )
    .number(
        attribute_name=ThirdReality24GRadarCluster.AttributeDefs.sensor_sensitivity.name,
        min_value=1,
        max_value=5,
        step=1,
        cluster_id=ThirdReality24GRadarCluster.cluster_id,
        translation_key="sensor_sensitivity",
        fallback_name="Sensor sensitivity",
    )
    .add_to_registry()
)
