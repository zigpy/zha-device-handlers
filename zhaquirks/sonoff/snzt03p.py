"""Sonoff SNZT-03P - Zigbee motion sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import LIGHT_LUX, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffPrivateCluster(CustomCluster):
    """Manufacturer-specific cluster for Sonoff SNZT-03P."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_private"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the Sonoff private cluster."""

        illumination_compensation = ZCLAttributeDef(
            id=0x2018,
            type=t.int16s,
            access="rw",
            manufacturer_code=None,
        )


(
    QuirkBuilder("SONOFF", "SNZT-03P")
    .applies_to("SONOFF", "SNZB-03PR2")
    .replaces(SonoffPrivateCluster)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OccupancySensing.cluster_id,
        function=lambda entity: (
            getattr(entity, "translation_key", None) == "pir_o_to_u_delay"
        ),
    )
    .number(
        attribute_name=OccupancySensing.AttributeDefs.pir_o_to_u_delay.name,
        cluster_id=OccupancySensing.cluster_id,
        min_value=5,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="detection_interval",
        fallback_name="Detection interval",
    )
    .number(
        attribute_name=SonoffPrivateCluster.AttributeDefs.illumination_compensation.name,
        cluster_id=SonoffPrivateCluster.cluster_id,
        min_value=-1000,
        max_value=1000,
        step=1,
        device_class=NumberDeviceClass.ILLUMINANCE,
        unit=LIGHT_LUX,
        translation_key="illuminance_offset",
        fallback_name="Illuminance offset",
    )
    .add_to_registry()
)
