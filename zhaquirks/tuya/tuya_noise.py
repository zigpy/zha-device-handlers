"""Tuya noise sensor."""

from zigpy import types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfSoundPressure,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaNoiseLevel(t.enum8):
    """Tuya noise level."""

    Quiet = 0x00
    Medium = 0x01
    Loud = 0x02


(
    TuyaQuirkBuilder("_TZE204_r6kfl9ta", "TS0601")  # ZY-N1 sound detector
    .tuya_sensor(
        dp_id=1,
        attribute_name="sound_pressure",
        type=t.uint32_t,
        device_class=SensorDeviceClass.SOUND_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfSoundPressure.DECIBEL,
        entity_type=EntityType.STANDARD,
        fallback_name="Sound pressure",
    )
    .tuya_enum(
        dp_id=8,
        attribute_name="noise_level",
        enum_class=TuyaNoiseLevel,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Report,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="noise_level",
        fallback_name="Noise level",
    )
    # DP 101 reports 0 while noise is detected, higher values while quiet
    .tuya_dp_attribute(
        dp_id=101,
        attribute_name="noise_detected",
        type=t.Bool,
        converter=lambda x: x == 0,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Report,
    )
    .binary_sensor(
        attribute_name="noise_detected",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.SOUND,
        fallback_name="Noise detected",
    )
    # Medium level boundary, noise is detected above this level
    .tuya_number(
        dp_id=16,
        attribute_name="noise_threshold",
        type=t.uint32_t,
        device_class=NumberDeviceClass.SOUND_PRESSURE,
        unit=UnitOfSoundPressure.DECIBEL,
        min_value=0,
        max_value=120,
        step=1,
        translation_key="noise_threshold",
        fallback_name="Noise threshold",
    )
    # Loud level boundary
    .tuya_number(
        dp_id=20,
        attribute_name="loud_threshold",
        type=t.uint32_t,
        device_class=NumberDeviceClass.SOUND_PRESSURE,
        unit=UnitOfSoundPressure.DECIBEL,
        min_value=0,
        max_value=120,
        step=1,
        translation_key="loud_threshold",
        fallback_name="Loud threshold",
    )
    # Quiet time before noise detection clears
    .tuya_number(
        dp_id=22,
        attribute_name="fading_time",
        type=t.uint32_t,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=300,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    # Sustained noise needed before detection
    .tuya_number(
        dp_id=103,
        attribute_name="detection_delay",
        type=t.uint32_t,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=300,
        step=1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    # The sound pressure DP is only sent on data query or when the noise level changes
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry()
)
