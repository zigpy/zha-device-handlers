"""Sonoff SNZB-03PR2 - Zigbee motion sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import LIGHT_LUX, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

SONOFF_PRIVATE_CLUSTER_ID = 0xFC11
SONOFF_ILLUM_COMP_ATTR_ID = 0x2018
PIROCCUPIEDTOUNOCCUPIEDDELAY_ATTR_ID = 0x0010


class SonoffPrivateCluster(CustomCluster):
    """Manufacturer-specific cluster for Sonoff SNZB-03PR2."""

    cluster_id = SONOFF_PRIVATE_CLUSTER_ID
    ep_attribute = "sonoff_private"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the Sonoff private cluster."""

        illumination_compensation = ZCLAttributeDef(
            id=SONOFF_ILLUM_COMP_ATTR_ID,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )


class SonoffOccupancyCluster(CustomCluster, OccupancySensing):
    """Occupancy sensing cluster for SNZB-03PR2."""

    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Custom occupancy-related attributes for SNZB-03PR2."""

        pir_occupied_to_unoccupied_delay = ZCLAttributeDef(
            id=PIROCCUPIEDTOUNOCCUPIEDDELAY_ATTR_ID,
            type=t.uint16_t,
            access="rw",
        )


(
    QuirkBuilder("SONOFF", "SNZB-03PR2")
    .replaces(SonoffPrivateCluster)
    .replaces(SonoffOccupancyCluster)
    .number(
        PIROCCUPIEDTOUNOCCUPIEDDELAY_ATTR_ID,
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
