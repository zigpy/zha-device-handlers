"""Tuya noise sensor."""

from zigpy import types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfSoundPressure,
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
    # The sound pressure DP is only sent on data query or when the noise level changes
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry()
)
