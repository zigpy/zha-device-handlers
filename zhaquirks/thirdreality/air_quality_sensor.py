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
            id=0x0000,
            type=t.Single,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RAQ1096Z")
    .replaces(ThirdRealityRadarCluster)
    .sensor(
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.voc_index.name,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        state_class=SensorStateClass.MEASUREMENT,
        unit="aqi",
        translation_key="voc_index",
        fallback_name="VOC index",
    )
    .add_to_registry()
)
