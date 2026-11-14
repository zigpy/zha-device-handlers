"""Sonoff SNZB-03P – stable ZHA quirk (practical version)."""

from zha.application.platforms.number import SonoffPresenceSenorTimeout
import zigpy.types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


# ---------------------------------------------------------------------
# Illumination (vendor-specific, read-only)
# ---------------------------------------------------------------------


class LastIlluminationState(t.enum8):
    """Enum representing the last illumination state reported by SNZB-03P."""

    Dark = 0x00
    Light = 0x01


class SonoffIlluminationCluster(CustomCluster):
    """Vendor-specific illumination cluster used by SNZB-03P."""

    cluster_id = 0xFC11
    name = "Sonoff illumination"
    ep_attribute = "sonoff_illumination"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the illumination cluster."""

        last_illumination_state = ZCLAttributeDef(
            id=0x2001,
            type=LastIlluminationState,
            access="p",
            manufacturer_code=None,
        )


# ---------------------------------------------------------------------
# Motion timeout
# ---------------------------------------------------------------------


class SNZB03PMotionTimeout(SonoffPresenceSenorTimeout):
    """Motion timeout, the SNZB-03P accepts 5 s and up."""

    _attr_native_min_value: int = 5
    _attr_native_unit_of_measurement: str = UnitOfTime.SECONDS
    _attr_device_class: NumberDeviceClass = NumberDeviceClass.DURATION


# ---------------------------------------------------------------------
# Quirk definition
# ---------------------------------------------------------------------

(
    QuirkBuilder("eWeLink", "SNZB-03P")
    # Add vendor illumination cluster
    .adds(SonoffIlluminationCluster)
    # Prevent default IAS Zone entity creation
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
    )
    # Replace native ZHA motion timeout entity, preserving its unique ID
    .replaces_entity(
        SonoffPresenceSenorTimeout,
        SNZB03PMotionTimeout,
        endpoint_id=1,
        cluster_id=OccupancySensing.cluster_id,
    )
    # Illumination state (dim / bright)
    .enum(
        attribute_name=SonoffIlluminationCluster.AttributeDefs.last_illumination_state.name,
        enum_class=LastIlluminationState,
        cluster_id=SonoffIlluminationCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="illumination",
        fallback_name="Illumination",
    )
    .add_to_registry()
)
