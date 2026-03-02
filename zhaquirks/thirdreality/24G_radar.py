"""Third Reality 24G radar sensor devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig, SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import CONCENTRATION_PARTS_PER_BILLION
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.measurement import FormaldehydeConcentration

from zhaquirks.tuya.builder import TuyaFormaldehydeConcentration
from zhaquirks.develco.air_quality import DevelcoVOCMeasurement


class ThirdRealityRadarCluster(CustomCluster):
    """Third Reality's 24G radar private cluster."""

    cluster_id = 0xff01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # reset the accumulated power of the plug
        senior_calibation: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        
        # reset the accumulated power of the plug
        senior_sensitive: Final = ZCLAttributeDef(
            id=0x0060,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

(
    QuirkBuilder("Third Reality, Inc", "3RPS01083Z")
    .replaces(ThirdRealityRadarCluster)
    .switch(
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.senior_calibation.name,
        translation_key="senior_calibation",
        fallback_name="Senior calibation",
    )
    .number(
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.senior_sensitive.name,
        min_value=1,
        max_value=5,
        step=1,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        translation_key="senior_sensitive",
        fallback_name="Senior sensitive",
    )
    .add_to_registry()
)