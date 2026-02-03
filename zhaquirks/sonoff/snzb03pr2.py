"""Sonoff SNZB-03PR2 - Zigbee motion sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import LIGHT_LUX, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class SonoffPrivateCluster(CustomCluster):
    """Manufacturer-specific cluster for Sonoff SNZB-03PR2."""

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
    QuirkBuilder("SONOFF", "SNZB-03PR2")
    .replaces(SonoffPrivateCluster)
    .number(
        OccupancySensing.AttributeDefs.pir_o_to_u_delay.id,
        OccupancySensing.cluster_id,
        min_value=5,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="detection_interval",
        fallback_name="Detection interval",
    )
    .number(
        SonoffPrivateCluster.AttributeDefs.illumination_compensation.id,
        SonoffPrivateCluster.cluster_id,
        min_value=-1000,
        max_value=1000,
        step=1,
        device_class=NumberDeviceClass.ILLUMINANCE,
        unit=LIGHT_LUX,
        translation_key="illuminance_compensation",
        fallback_name="Illuminance compensation",
    )
    .add_to_registry()
)
