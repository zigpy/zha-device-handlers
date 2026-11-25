"""Heiman M1P-E smart occupancy sensor."""

from typing import Final

from zha.application.platforms.number import (
    PIROccupiedToUnoccupiedDelayConfigurationEntity,
)
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    LIGHT_LUX,
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class SensitivityLevel(t.enum8):
    """Occupancy sensitivity levels."""

    Low = 0
    Medium = 1
    High = 2


class WorkMode(t.enum8):
    """Occupancy detection modes."""

    PIR = 1
    Radar = 2
    PIR_and_radar = 3


class RadarLearningState(t.enum8):
    """Radar background learning states."""

    Normal = 0
    Learning = 1
    Completed = 2
    Failed = 3


class CustomHeimanCluster(CustomCluster):
    """M1P-E settings and diagnostics from the Heiman private cluster."""

    cluster_id = 0xFC90
    name = "Heiman M1P-E"
    ep_attribute = "heiman_m1p"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        sensor_fault_state: Final = ZCLAttributeDef(
            id=0x0002, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        sensor_sensitivity_level: Final = ZCLAttributeDef(
            id=0x0004, type=t.uint8_t, manufacturer_code=0x120B
        )
        rebooted_count: Final = ZCLAttributeDef(
            id=0x0019, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        rejoined_count: Final = ZCLAttributeDef(
            id=0x001A, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        reported_packages: Final = ZCLAttributeDef(
            id=0x001B, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        work_mode: Final = ZCLAttributeDef(
            id=0x001E, type=t.bitmap8, manufacturer_code=0x120B
        )
        radar_learning_control: Final = ZCLAttributeDef(
            id=0x0027, type=t.uint16_t, manufacturer_code=0x120B
        )
        radar_learning_state: Final = ZCLAttributeDef(
            id=0x0028, type=RadarLearningState, access="rp", manufacturer_code=0x120B
        )
        radar_detection_target_range: Final = ZCLAttributeDef(
            id=0x0029, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        illuminance_threshold: Final = ZCLAttributeDef(
            id=0x002A, type=t.uint16_t, manufacturer_code=0x120B
        )
        radar_detection_max_range: Final = ZCLAttributeDef(
            id=0x002C, type=t.uint16_t, manufacturer_code=0x120B
        )
        work_indicator: Final = ZCLAttributeDef(
            id=0x1004, type=t.uint8_t, manufacturer_code=0x120B
        )
        temperature_offset: Final = ZCLAttributeDef(
            id=0x100D, type=t.int16s, manufacturer_code=0x120B
        )
        humidity_offset: Final = ZCLAttributeDef(
            id=0x1012, type=t.int16s, manufacturer_code=0x120B
        )


# Battery, occupancy, illuminance and temperature on endpoint 1, and humidity on
# endpoint 2, are discovered through their standard ZCL clusters by ZHA.
(
    QuirkBuilder("Heiman", "M1P-E")
    .applies_to("Heiman", "M1-PE")
    .applies_to("HEIMAN", "M1P-E")
    .applies_to("HEIMAN", "M1-PE")
    .friendly_name(manufacturer="Heiman", model="M1P-E")
    .replaces(CustomHeimanCluster)
    # The OnOff client controls other devices; it is not an opening sensor.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
    )
    .binary_sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.sensor_fault_state.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        device_class=BinarySensorDeviceClass.PROBLEM,
        fallback_name="Fault",
    )
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.radar_detection_target_range.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        divisor=100,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfLength.METERS,
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    # Replace the default delay number to enforce the device's 5..3600 s range.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OccupancySensing.cluster_id,
        function=lambda entity: (
            type(entity) is PIROccupiedToUnoccupiedDelayConfigurationEntity
        ),
    )
    .number(
        attribute_name=OccupancySensing.AttributeDefs.pir_o_to_u_delay.name,
        cluster_id=OccupancySensing.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=5,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        # Include the cluster ID to preserve the ZHA-native entity's unique ID.
        unique_id_suffix=f"{OccupancySensing.cluster_id}-pir_o_to_u_delay",
        translation_key="pir_o_to_u_delay",
        fallback_name="Unoccupied delay",
    )
    .number(
        attribute_name=CustomHeimanCluster.AttributeDefs.radar_detection_max_range.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=0,
        max_value=6,
        step=0.25,
        multiplier=0.01,
        unit=UnitOfLength.METERS,
        translation_key="radar_detection_max_range",
        fallback_name="Radar detection maximum range",
    )
    .number(
        attribute_name=CustomHeimanCluster.AttributeDefs.illuminance_threshold.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=0,
        max_value=1000,
        step=1,
        unit=LIGHT_LUX,
        translation_key="illuminance_threshold",
        fallback_name="Illuminance threshold",
    )
    .enum(
        attribute_name=CustomHeimanCluster.AttributeDefs.sensor_sensitivity_level.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        enum_class=SensitivityLevel,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .enum(
        attribute_name=CustomHeimanCluster.AttributeDefs.work_mode.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        enum_class=WorkMode,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    .number(
        attribute_name=CustomHeimanCluster.AttributeDefs.temperature_offset.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=-15,
        max_value=15,
        step=0.1,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        attribute_name=CustomHeimanCluster.AttributeDefs.humidity_offset.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=-15,
        max_value=15,
        step=0.1,
        multiplier=0.01,
        unit=PERCENTAGE,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    # These are actions, so expose buttons with distinct unique ID suffixes.
    .write_attr_button(
        attribute_name=CustomHeimanCluster.AttributeDefs.radar_learning_control.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_value=0xFFFE,
        unique_id_suffix="radar_learning_start",
        translation_key="radar_learning_start",
        fallback_name="Start radar learning",
    )
    .write_attr_button(
        attribute_name=CustomHeimanCluster.AttributeDefs.radar_learning_control.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_value=0xFFFF,
        unique_id_suffix="radar_learning_reset",
        translation_key="radar_learning_reset",
        fallback_name="Reset radar learning",
    )
    .enum(
        attribute_name=CustomHeimanCluster.AttributeDefs.radar_learning_state.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        enum_class=RadarLearningState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="radar_learning_state",
        fallback_name="Radar learning state",
    )
    .switch(
        attribute_name=CustomHeimanCluster.AttributeDefs.work_indicator.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="work_indicator",
        fallback_name="Work indicator",
    )
    # Zigbee debug sensors:
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.rebooted_count.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rebooted_count",
        fallback_name="Rebooted count",
    )
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.rejoined_count.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="rejoined_count",
        fallback_name="Rejoined count",
    )
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.reported_packages.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        attribute_initialized_from_cache=False,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="reported_packages",
        fallback_name="Reported packages",
    )
    .add_to_registry()
)
