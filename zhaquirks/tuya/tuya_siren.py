"""Tuya Siren."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t

from zhaquirks.tuya import TuyaPowerConfigurationClusterOther
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaSirenState(t.enum8):
    """Tuya siren state enum."""

    Sound = 0x00
    Light = 0x01
    Sound_and_light = 0x02
    Normal = 0x03


class TuyaSirenRingtone(t.enum8):
    """Tuya siren ringtone enum."""

    Ringtone_01 = 0x00
    Ringtone_02 = 0x01
    Ringtone_03 = 0x02


(
    TuyaQuirkBuilder("_TZE204_nlrfgpny", "TS0601")
    .tuya_enum(
        dp_id=1,
        attribute_name="alarm_state",
        enum_class=TuyaSirenState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="alarm_state",
        fallback_name="Alarm state",
    )
    .tuya_binary_sensor(
        dp_id=6,
        attribute_name="charge_state",
        translation_key="charge_state",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        fallback_name="Charge state",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="alarm_duration",
        min_value=1,
        type=t.uint16_t,
        max_value=60,
        step=1,
        unit=UnitOfTime.MINUTES,
        translation_key="alarm_duration",
        fallback_name="Alarm duration",
    )
    .tuya_switch(
        dp_id=13,
        attribute_name="siren_on",
        entity_type=EntityType.STANDARD,
        translation_key="siren_on",
        fallback_name="Siren on",
    )
    .tuya_battery(dp_id=15, power_cfg=TuyaPowerConfigurationClusterOther)
    .tuya_binary_sensor(
        dp_id=20,
        attribute_name="tamper_state",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.STANDARD,
        translation_key="tamper_state",
        fallback_name="Tamper state",
    )
    .tuya_enum(
        dp_id=21,
        attribute_name="alarm_ringtone",
        enum_class=TuyaSirenRingtone,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="enable_tamper_alarm",
        entity_type=EntityType.STANDARD,
        translation_key="enable_tamper_alarm",
        fallback_name="Enable tamper alarm",
    )
    .tuya_enum(
        dp_id=102,
        attribute_name="alarm_mode",
        enum_class=TuyaSirenState,
        translation_key="alarm_mode",
        fallback_name="Alarm mode",
    )
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
