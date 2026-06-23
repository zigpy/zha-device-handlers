"""Third Reality air quality sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig, SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityAirQualityCluster(CustomCluster):
    """Third Reality's air quality sensor private cluster."""

    cluster_id = 0x042e

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        voc_Index: Final = ZCLAttributeDef(
            id=0x0100,
            type=t.Single,
            manufacturer_code=0x1407,
        )

(
    QuirkBuilder("Third Reality, Inc", "3RAQ1096Z")
    .replaces(ThirdRealityAirQualityCluster)
    .sensor(
        endpoint_id=1,
        attribute_name=ThirdRealityAirQualityCluster.AttributeDefs.voc_Index.name,
        cluster_id=ThirdRealityAirQualityCluster.cluster_id,
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="voc_index",
        fallback_name="VOC index",
    )
    .add_to_registry()
)