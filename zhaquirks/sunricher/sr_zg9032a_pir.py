"""Sunricher SR-ZG9032A-PIR motion sensor + light sensor + dimmer."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef

SUNRICHER_MANUFACTURER_CODE = 0x1224


class SunricherPIRBasicCluster(CustomCluster, Basic):
    """Sunricher Basic cluster with manufacturer-specific attributes."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        motion_sensor_lux_threshold: Final = ZCLAttributeDef(
            id=0x8903,
            type=t.uint16_t,
            manufacturer_code=SUNRICHER_MANUFACTURER_CODE,
        )
        motion_sensor_sensitivity: Final = ZCLAttributeDef(
            id=0x8905,
            type=t.uint8_t,
            manufacturer_code=SUNRICHER_MANUFACTURER_CODE,
        )
        pwm_output_percentage: Final = ZCLAttributeDef(
            id=0x8909,
            type=t.uint8_t,
            manufacturer_code=SUNRICHER_MANUFACTURER_CODE,
        )
        linearity_error_ratio_lux: Final = ZCLAttributeDef(
            id=0x890D,
            type=t.uint16_t,
            manufacturer_code=SUNRICHER_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("Sunricher", "HK-DIM-PIR")
    .friendly_name(
        manufacturer="Sunricher",
        model="SR-ZG9032A-PIR",
    )
    .replaces(SunricherPIRBasicCluster)
    .number(
        SunricherPIRBasicCluster.AttributeDefs.motion_sensor_lux_threshold.name,
        SunricherPIRBasicCluster.cluster_id,
        min_value=0,
        max_value=65535,
        entity_type=EntityType.CONFIG,
        translation_key="motion_sensor_lux_threshold",
        fallback_name="Daylight sensor lux threshold",
    )
    .number(
        SunricherPIRBasicCluster.AttributeDefs.motion_sensor_sensitivity.name,
        SunricherPIRBasicCluster.cluster_id,
        min_value=0,
        max_value=15,
        entity_type=EntityType.CONFIG,
        translation_key="motion_sensor_sensitivity",
        fallback_name="Motion sensor sensitivity",
    )
    .number(
        SunricherPIRBasicCluster.AttributeDefs.pwm_output_percentage.name,
        SunricherPIRBasicCluster.cluster_id,
        min_value=0,
        max_value=254,
        unit="%",
        entity_type=EntityType.CONFIG,
        translation_key="pwm_output_percentage",
        fallback_name="PWM output percentage",
    )
    .number(
        SunricherPIRBasicCluster.AttributeDefs.linearity_error_ratio_lux.name,
        SunricherPIRBasicCluster.cluster_id,
        min_value=100,
        max_value=10000,
        entity_type=EntityType.CONFIG,
        translation_key="linearity_error_ratio_lux",
        fallback_name="Linearity error ratio coefficient",
    )
    .add_to_registry()
)
