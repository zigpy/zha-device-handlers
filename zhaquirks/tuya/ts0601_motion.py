"""Quirk for the Mercator Ikuü TS0601 motion sensor (_TZE200_agumlajc)."""

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class LightControlMode(t.enum8):
    """Enum for the backlight mode setting (dp_id=105)."""

    On = 0
    Off = 1
    Auto = 2


# Quirk definition for the Mercator Ikuu Combination Sensor (_TZE200_agumlajc)
(
    TuyaQuirkBuilder("_TZE200_agumlajc", "TS0601")
    .applies_to("_TZE204_agumlajc", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_illuminance(dp_id=101)
    .tuya_number(
        dp_id=102,
        attribute_name="brightness_threshold",
        type=t.uint16_t,
        device_class=SensorDeviceClass.ILLUMINANCE,
        min_value=0,
        max_value=1000,
        step=1,
        translation_key="brightness_threshold",
        fallback_name="Brightness Threshold",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="motion_hold_time",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=3600,
        step=1,
        translation_key="motion_hold_time",
        fallback_name="Motion Hold Time",
    )
    .tuya_binary_sensor(
        dp_id=104,
        attribute_name="motion",
        device_class=BinarySensorDeviceClass.MOTION,
        entity_type=EntityType.STANDARD,
        translation_key="motion",
        fallback_name="Motion",
    )
    .tuya_enum(
        dp_id=105,
        attribute_name="light_control_mode",
        enum_class=LightControlMode,
        translation_key="light_control_mode",
        fallback_name="Light Control Mode",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="motion_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="motion_sensitivity",
        fallback_name="Motion Sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)
