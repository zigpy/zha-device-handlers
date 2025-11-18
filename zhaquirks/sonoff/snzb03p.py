"""Sonoff SNZB-03P - Zigbee motion sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef, ZCLHeader


class LastIlluminationState(t.enum8):
    """Last measureed state of illumination enum."""

    Dark = 0x00
    Light = 0x01


class SonoffIlluminationCluster(CustomCluster):
    """Custom Sonoff illumination cluster."""

    cluster_id = 0xFC11
    manufacturer_id_override: t.uint16_t = ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        last_illumination_state = ZCLAttributeDef(
            id=0x2001,
            type=LastIlluminationState,
            access="rp",
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("eWeLink", "SNZB-03P")
    .replaces(SonoffIlluminationCluster)
    .removes(IasZone.cluster_id)  #  IasZone cluster 0x0500: remove motion detection
    .number(
        OccupancySensing.AttributeDefs.ultrasonic_o_to_u_delay.name,
        OccupancySensing.cluster_id,
        min_value=5,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="motion_timeout",
        fallback_name="Presence detection timeout",
    )
    .enum(
        SonoffIlluminationCluster.AttributeDefs.last_illumination_state.name,
        LastIlluminationState,
        SonoffIlluminationCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="last_illumination_state",
        fallback_name="Last illumination state",
    )
    .add_to_registry()
)
