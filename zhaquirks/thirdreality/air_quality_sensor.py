"""Third Reality air quality sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityRadarCluster(CustomCluster):
    """Third Reality's air quality sensor private cluster."""

    cluster_id = 0x042E

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        voc_index: Final = ZCLAttributeDef(
            id=0x0100,
            type=t.Single,
            manufacturer_code=0x1407,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RAQ1096Z")
    .replaces(ThirdRealityRadarCluster)
    .sensor(
        endpoint_id=1,
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.voc_index.name,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        unit=" ",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="VOC_index",
        fallback_name="Voc index",
    )
    .add_to_registry()
)
