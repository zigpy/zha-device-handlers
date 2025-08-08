"""Quirks v2 for Tuya vibration sensor with accelerometer data (_TZE200_iba1ckek)."""

"""ts0601_vibration_TZE200_v2.py"""

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t


def uint_to_sint(value: t.uint8_t) -> t.int8s:
    if value > 127:
      value = value - 256
    return value


(
    TuyaQuirkBuilder("_TZE200_iba1ckek", "TS0601")
    .skip_configuration()
    # Acceleration sensors (raw values 0..255)
    .tuya_sensor(
        dp_id=101,
        attribute_name="x_axis",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ACCELERATION,
        entity_type=EntityType.STANDARD,
        translation_key="x_axis_acceleration",
        fallback_name="X-axis Acceleration",
        converter=uint_to_sint,
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="y_axis",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ACCELERATION,
        entity_type=EntityType.STANDARD,
        translation_key="y_axis_acceleration",
        fallback_name="Y-axis Acceleration",
        converter=uint_to_sint,
    )
    .tuya_sensor(
        dp_id=103,
        attribute_name="z_axis",
        type=t.uint8_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ACCELERATION,
        entity_type=EntityType.STANDARD,
        translation_key="z_axis_acceleration",
        fallback_name="Z-axis Acceleration",
        converter=uint_to_sint,
    )
    .add_to_registry()
)

