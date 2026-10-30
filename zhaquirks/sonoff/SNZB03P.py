"""Sonoff SNZB-03P – stable ZHA quirk (practical version)."""

from zha.application import EntityPlatform, EntityType
from zha.application.platforms.number.device_class import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef, ZCLHeader

from zhaquirks.builder import QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster

# ---------------------------------------------------------------------
# Illumination (vendor-specific, read-only)
# ---------------------------------------------------------------------


class LastIlluminationState(t.enum8):
    """Enum representing the last illumination state reported by SNZB‑03P."""

    Dark = 0x00
    Light = 0x01


class SonoffIlluminationCluster(CustomCluster):
    """Vendor-specific illumination cluster used by SNZB‑03P."""

    cluster_id = 0xFC11
    manufacturer_id_override = ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the illumination cluster."""

        last_illumination_state = ZCLAttributeDef(
            id=0x2001,
            type=LastIlluminationState,
            access="rp",
            is_manufacturer_specific=True,
        )


# ---------------------------------------------------------------------
# Quirk definition
# ---------------------------------------------------------------------

(
    QuirkBuilder("eWeLink", "SNZB-03P")
    # Vendor illumination cluster
    .replaces(SonoffIlluminationCluster)
    # Remove IAS motion to avoid duplicate binary_sensor
    .removes(IasZone.cluster_id)
    # Motion timeout (mapped by Sonoff to OccupancySensing delay)
    .number(
        OccupancySensing.AttributeDefs.ultrasonic_o_to_u_delay.name,
        OccupancySensing.cluster_id,
        min_value=5,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="motion_timeout",
        fallback_name="Motion timeout",
    )
    # Illumination state (dim / bright)
    .enum(
        SonoffIlluminationCluster.AttributeDefs.last_illumination_state.name,
        LastIlluminationState,
        SonoffIlluminationCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="illumination",
        fallback_name="Illumination",
    )
    .add_to_registry()
)
