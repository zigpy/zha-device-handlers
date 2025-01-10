"""Tuya Siren."""

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
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
    .tuya_binary_sensor(
        dp_id=1,
        attribute_name="alarm_state",
        translation_key="alarm_state",
        fallback_name="Alarm state",
    )
    .tuya_binary_sensor(
        dp_id=6,
        attribute_name="charge_state",
        translation_key="charge_state",
        fallback_name="Charge state",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="alarm_duration",
        min_value=1,
        type=t.uint16_t,
        max_value=60,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="alarm_duration",
        fallback_name="Alarm duration",
    )
    .tuya_switch(
        dp_id=13,
        attribute_name="alarm_switch",
        entity_type=EntityType.STANDARD,
        translation_key="alarm_switch",
        fallback_name="Alarm trigger",
    )
    .tuya_battery(dp_id=15, power_cfg=TuyaPowerConfigurationClusterOther)
    .tuya_contact(dp_id=20)
    .tuya_enum(
        dp_id=21,
        attribute_name="alarm_ringtone",
        enum_class=TuyaSirenRingtone,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="tamper_alarm_switch",
        entity_type=EntityType.STANDARD,
        translation_key="tamper_alarm_switch",
        fallback_name="Clear tamper alarm",
    )
    .tuya_enum(
        dp_id=102,
        attribute_name="alarm_state",
        enum_class=TuyaSirenState,
        translation_key="alarm_state",
        fallback_name="Alarm State",
    )
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
