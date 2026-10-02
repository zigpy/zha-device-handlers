"""Tuya water leak sensor."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.types import enum8

from zhaquirks.const import BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class AlarmMode(enum8):
    """Alarm mode of the sensor, which can be configured by user."""

    WATER_PRESENCE = 0x00
    WATER_ABSENCE = 0x01


class Ringtone(enum8):
    """Alarm tone of the sensor, which can be configured by user."""

    MUTED = 0x00
    TONE_1 = 0x01
    TONE_2 = 0x02
    TONE_3 = 0x03


# <SimpleDescriptor endpoint=1 profile=260 device_type=81
# device_version=1
# input_clusters=[4, 5, 61184, 0, 60672]
# output_clusters=[25, 10]>
(
    TuyaQuirkBuilder("_TZE284_1di7ujzp", "TS0601")
    .tuya_binary_sensor(  # Water presence (DP 1)
        dp_id=1,
        attribute_name="water_presence",
        device_class=BinarySensorDeviceClass.MOISTURE,
        fallback_name="Water presence",
    )
    .tuya_binary_sensor(  # Water leak (DP 102)
        dp_id=102,
        attribute_name="water_leak",
        device_class=BinarySensorDeviceClass.PROBLEM,
        fallback_name="Water leak",
    )
    .tuya_battery(  # Battery (DP 4)
        dp_id=4, battery_type=BatterySize.AAA, battery_qty=2
    )
    .tuya_enum(  # Alarm mode (DP 101)
        dp_id=101,
        attribute_name="alarm_mode",
        enum_class=AlarmMode,
        translation_key="alarm_mode",
        fallback_name="Alarm mode",
        entity_type=EntityType.CONFIG,
    )
    .tuya_enum(  # Ringtone (DP 103)
        dp_id=103,
        attribute_name="ringtone",
        enum_class=Ringtone,
        translation_key="ringtone",
        fallback_name="Ringtone",
        entity_type=EntityType.CONFIG,
    )
    .replaces_endpoint(1, device_type=zha.DeviceType.IAS_ZONE)
    .skip_configuration()
    .add_to_registry()
)
