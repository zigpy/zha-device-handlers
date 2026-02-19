"""Nous E10 CO2, Temperature, and Humidity Detector.

The quirk applies to the Zorro Alert ZR360CDB as well, which appears to be
identical to the Nous E10.

The quirk was developed based on the Zigbee2MQTT device definition:
    https://github.com/Koenkk/zigbee-herdsman-converters/blob/7eb0b699e500bb945a45bd3533fe0b5a47c721e6/src/devices/tuya.ts#L17480
"""

from zigpy.quirks.v2 import EntityPlatform, EntityType
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class AirQuality(t.enum8):
    """Tuya air quality enum."""

    excellent = 0x00
    moderate = 0x01
    poor = 0x02


class AlarmRingtone(t.enum8):
    """Tuya alarm ringtone enum."""

    volume_low = 0x00
    volume_high = 0x01
    OFF = 0x02


class BatteryState(t.enum8):
    """Tuya battery state enum."""

    low = 0x00
    medium = 0x01
    high = 0x02


(
    TuyaQuirkBuilder("_TZE200_pl31aqf5", "TS0601")
    .applies_to("_TZE200_xpvamyfz", "TS0601")
    .applies_to("_TZE284_xpvamyfz", "TS0601")
    .tuya_enum(
        dp_id=1,
        attribute_name="air_quality",
        enum_class=AirQuality,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="air_quality",
        fallback_name="Air quality",
    )
    .tuya_co2(dp_id=2)
    .tuya_enum(
        dp_id=5,
        attribute_name="alarm_ringtone",
        enum_class=AlarmRingtone,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .tuya_enum(
        dp_id=14,
        attribute_name="battery_state",
        enum_class=BatteryState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="battery_state",
        fallback_name="Battery state",
    )
    .tuya_number(
        dp_id=17,
        attribute_name="backlight_mode",
        type=t.uint16_t,
        min_value=1,
        max_value=3,
        step=1,
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_temperature(dp_id=18)
    .tuya_humidity(dp_id=19)
    .skip_configuration()
    .add_to_registry()
)
