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

        # calibrate of the plug
        sensor_calibration: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        # set the sensitive of the plug
        sensor_sensitive: Final = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RPS01083Z")
    .replaces(ThirdReality24GRadarCluster)
    .switch(
        cluster_id=ThirdReality24GRadarCluster.cluster_id,
        attribute_name=ThirdReality24GRadarCluster.AttributeDefs.sensor_calibration.name,
        translation_key="sensor_calibration",
        fallback_name="Sensor calibration",
    )
    .number(
        attribute_name=ThirdReality24GRadarCluster.AttributeDefs.sensor_sensitive.name,
        min_value=1,
        max_value=5,
        step=1,
        cluster_id=ThirdReality24GRadarCluster.cluster_id,
        translation_key="sensor_sensitive",
        fallback_name="Sensor sensitive",
    )
    .add_to_registry()
)
