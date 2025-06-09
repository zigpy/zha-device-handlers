"""Tuya Siren."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature, UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t

from zhaquirks.const import BatterySize
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


class TuyaSirenRingtoneV02(t.enum8):
    """Tuya siren ringtone variation 02 enum."""

    Ringtone_01 = 0x00
    Ringtone_02 = 0x01
    Ringtone_03 = 0x02
    Ringtone_04 = 0x03
    Ringtone_05 = 0x04
    Ringtone_06 = 0x05
    Ringtone_07 = 0x06
    Ringtone_08 = 0x07
    Door = 0x08
    Water = 0x09
    Temperature = 0x0A
    Entered = 0x0B
    Left = 0x0C


class TuyaAlarmVolume(t.enum8):
    """Tuya alarm volume enum."""

    Low = 0x00
    Medium = 0x01
    High = 0x02
    Mute = 0x03


class NeoAlarmVolume(t.enum8):
    """Neo alarm volume enum."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class NeoAlarmMelody18(t.enum8):
    """Neo alarm melody 18 step enum."""

    Melody_01 = 0x00
    Melody_02 = 0x01
    Melody_03 = 0x02
    Melody_04 = 0x03
    Melody_05 = 0x04
    Melody_06 = 0x05
    Melody_07 = 0x06
    Melody_08 = 0x07
    Melody_09 = 0x08
    Melody_10 = 0x09
    Melody_11 = 0x0A
    Melody_12 = 0x0B
    Melody_13 = 0x0C
    Melody_14 = 0x0D
    Melody_15 = 0x0E
    Melody_16 = 0x0F
    Melody_17 = 0x10
    Melody_18 = 0x11


class NeoAlarmMelody32(t.enum8):
    """Neo alarm melody 32 step enum."""

    Melody_01 = 0x00
    Melody_02 = 0x01
    Melody_03 = 0x02
    Melody_04 = 0x03
    Melody_05 = 0x04
    Melody_06 = 0x05
    Melody_07 = 0x06
    Melody_08 = 0x07
    Melody_09 = 0x08
    Melody_10 = 0x09
    Melody_11 = 0x0A
    Melody_12 = 0x0B
    Melody_13 = 0x0C
    Melody_14 = 0x0D
    Melody_15 = 0x0E
    Melody_16 = 0x0F
    Melody_17 = 0x10
    Melody_18 = 0x11
    Melody_19 = 0x12
    Melody_20 = 0x13
    Melody_21 = 0x14
    Melody_22 = 0x15
    Melody_23 = 0x16
    Melody_24 = 0x17
    Melody_25 = 0x18
    Melody_26 = 0x19
    Melody_27 = 0x1A
    Melody_28 = 0x1B
    Melody_29 = 0x1C
    Melody_30 = 0x1D
    Melody_31 = 0x1E
    Melody_32 = 0x1F


class NeoBatteryState(t.enum8):
    """Neo battery state enum."""

    Full = 0x00
    High = 0x01
    Medium = 0x02
    Low = 0x03
    USB = 0x04


(
    TuyaQuirkBuilder("_TZE204_nlrfgpny", "TS0601")
    .applies_to("TZE200_nlrfgpny", "TS0601")
    .applies_to("_TZE284_nlrfgpny", "TS0601")
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
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        fallback_name="Charging",
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
    .tuya_battery(
        dp_id=15, battery_type=BatterySize.Other, battery_qty=1, battery_voltage=30
    )
    .tuya_binary_sensor(
        dp_id=20,
        attribute_name="tamper",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_type=EntityType.STANDARD,
        fallback_name="Tamper",
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


# Neo NAS-AB02B0 - Temperature & humidity sensor and alarm
(
    TuyaQuirkBuilder("_TZE200_d0yu2xgi", "TS0601")
    .applies_to("_TYST11_d0yu2xgi", "0yu2xgi")
    .tuya_enum(
        dp_id=101,
        attribute_name="power_type",
        enum_class=NeoBatteryState,
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="power_type",
        fallback_name="Power type",
    )
    .tuya_enum(
        dp_id=102,
        attribute_name="alarm_ringtone",
        enum_class=NeoAlarmMelody18,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="alarm_duration",
        min_value=0,
        type=t.uint16_t,
        max_value=1800,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="alarm_duration",
        fallback_name="Alarm duration",
    )
    .tuya_onoff(dp_id=104)
    .tuya_temperature(dp_id=105, scale=10)
    .tuya_humidity(dp_id=106)
    .tuya_number(
        dp_id=107,
        attribute_name="alarm_temperature_min",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-20,
        max_value=80,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_temperature_min",
        fallback_name="Alarm temperature min",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="alarm_temperature_max",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-20,
        max_value=80,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_temperature_max",
        fallback_name="Alarm temperature max",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="alarm_humidity_min",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_humidity_min",
        fallback_name="Alarm humidity min",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="alarm_humidity_max",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_humidity_max",
        fallback_name="Alarm humidity max",
    )
    .tuya_switch(
        dp_id=113,
        attribute_name="temperature_alarm",
        translation_key="temperature_alarm",
        fallback_name="Temperature alarm",
    )
    # 112 skipped, unknown
    .tuya_switch(
        dp_id=114,
        attribute_name="humidity_alarm",
        translation_key="humidity_alarm",
        fallback_name="Humidity alarm",
    )
    # 115 skipped, unknown
    .tuya_enum(
        dp_id=116,
        attribute_name="alarm_volume",
        enum_class=NeoAlarmVolume,
        translation_key="alarm_volume",
        fallback_name="Alarm volume",
    )
    .skip_configuration()
    .add_to_registry()
)


# Neo NAS-AB02B2
(
    TuyaQuirkBuilder("_TZE200_t1blo2bj", "TS0601")
    .applies_to("_TZE204_t1blo2bj", "TS0601")
    .applies_to("_TZE204_q76rtoa9", "TS0601")
    .tuya_enum(
        dp_id=5,
        attribute_name="alarm_volume",
        enum_class=NeoAlarmVolume,
        translation_key="alarm_volume",
        fallback_name="Alarm volume",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="alarm_duration",
        min_value=0,
        type=t.uint16_t,
        max_value=1800,
        step=1,
        unit=UnitOfTime.SECONDS,
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
    .tuya_battery(
        dp_id=15, battery_type=BatterySize.Other, battery_qty=1, battery_voltage=30
    )
    .tuya_enum(
        dp_id=21,
        attribute_name="alarm_ringtone",
        enum_class=NeoAlarmMelody18,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya ZA03
(
    TuyaQuirkBuilder("_TZE204_hcxvyxa5", "TS0601")
    .tuya_enum(
        dp_id=5,
        attribute_name="alarm_volume",
        enum_class=TuyaAlarmVolume,
        translation_key="alarm_volume",
        fallback_name="Alarm volume",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="alarm_duration",
        min_value=0,
        type=t.uint16_t,
        max_value=380,
        step=1,
        unit=UnitOfTime.SECONDS,
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
    .tuya_enum(
        dp_id=21,
        attribute_name="alarm_ringtone",
        enum_class=NeoAlarmMelody32,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya smart siren
(
    TuyaQuirkBuilder("_TZE204_k7mfgaen", "TS0601")
    .applies_to("_TZE204_fncxk3ob", "TS0601")
    .tuya_enum(
        dp_id=1,
        attribute_name="alarm_mode",
        enum_class=TuyaSirenState,
        translation_key="alarm_mode",
        fallback_name="Alarm mode",
    )
    .tuya_enum(
        dp_id=5,
        attribute_name="alarm_volume",
        enum_class=TuyaAlarmVolume,
        translation_key="alarm_volume",
        fallback_name="Alarm volume",
    )
    .tuya_binary_sensor(
        dp_id=6,
        attribute_name="charge_state",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        fallback_name="Charging",
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
    # DP 14, battery level enum skipped
    .tuya_battery(
        dp_id=15, battery_type=BatterySize.Other, battery_qty=1, battery_voltage=30
    )
    .tuya_enum(
        dp_id=21,
        attribute_name="alarm_ringtone",
        enum_class=TuyaSirenRingtoneV02,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .skip_configuration()
    .add_to_registry()
)
