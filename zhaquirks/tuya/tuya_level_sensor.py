"""Tuya Ultrasonic Level Sensors."""

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfLength
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaLiquidState(t.enum8):
    """Tuya Liquid State Enum."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


base_level_quirk = (
    TuyaQuirkBuilder()
    .tuya_enum(
        dp_id=1,
        attribute_name="liquid_state",
        enum_class=TuyaLiquidState,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="liquid_state",
        fallback_name="Liquid state",
    )
    .tuya_sensor(
        dp_id=2,
        attribute_name="liquid_depth",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        entity_type=EntityType.STANDARD,
        translation_key="liquid_depth",
        fallback_name="Liquid depth",
    )
    .tuya_sensor(
        dp_id=22,
        attribute_name="liquid_level_percent",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        entity_type=EntityType.STANDARD,
        translation_key="liquid_level_percent",
        fallback_name="Liquid level ratio",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="max_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="max_set",
        fallback_name="Liquid max percentage",
    )
    .tuya_number(
        dp_id=8,
        attribute_name="mini_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="mini_set",
        fallback_name="Liquid minimal percentage",
    )
    .skip_configuration()
)


(
    base_level_quirk.clone()
    .applies_to("_TZE284_kyyu8rbj", "TS0601")
    .tuya_number(
        dp_id=19,
        attribute_name="installation_height",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=10,
        max_value=400,
        step=1,
        translation_key="installation_height",
        fallback_name="Height from sensor to tank bottom",
    )
    .tuya_number(
        dp_id=21,
        attribute_name="liquid_depth_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.CENTIMETERS,
        min_value=10,
        max_value=400,
        step=1,
        translation_key="liquid_depth_max",
        fallback_name="Height from sensor to liquid level",
    )
    .add_to_registry()
)


(
    base_level_quirk.clone()
    .applies_to("_TZE200_lvkk0hdg", "TS0601")
    .tuya_number(
        dp_id=19,
        attribute_name="installation_height",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.MILLIMETERS,
        min_value=10,
        max_value=4000,
        step=1,
        translation_key="installation_height",
        fallback_name="Height from sensor to tank bottom",
    )
    .tuya_number(
        dp_id=21,
        attribute_name="liquid_depth_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.MILLIMETERS,
        min_value=10,
        max_value=4000,
        step=1,
        translation_key="liquid_depth_max",
        fallback_name="Height from sensor to liquid level",
    )
    .add_to_registry()
)
