"""Tuya Light and Fan Speed switches."""

import zigpy.types as t
from zhaquirks.builder import (
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
from zhaquirks.tuya import PowerOnState
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import MoesBacklight


class TuyaSpeedFan(t.enum8):
    """Tuya speed fan enum."""

    min = 0x00
    low = 0x01
    mid = 0x02
    high = 0x03
    max = 0x04


# Fan and Light Switch
(
    TuyaQuirkBuilder(
        "_TZE204_ft3laxaa", "TS0601"
    )  # MakeGood Fan Speed Controller and Light Switch with Power Metering
    .tuya_switch(
        dp_id=1,
        attribute_name="fan_switch",
        translation_key="fan_switch",
        fallback_name="Fan Switch",
        entity_type=EntityType.STANDARD,
    )
    .tuya_number(
        dp_id=2,
        attribute_name="fan_timer",
        translation_key="fan_timer",
        type=t.uint32_t,
        fallback_name="Fan Timer",
        min_value=0,
        max_value=600,
        step=1,
        multiplier=1 / 60,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=3,
        enum_class=TuyaSpeedFan,
        attribute_name="fan_speed",
        translation_key="fan_speed",
        fallback_name="Fan Speed",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_number(
        dp_id=7,
        attribute_name="switch_1_timer",
        translation_key="switch_1_timer",
        type=t.uint32_t,
        fallback_name="Switch 1 Timer",
        min_value=0,
        max_value=600,
        step=1,
        multiplier=1 / 60,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=11,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power on state",
        entity_type=EntityType.CONFIG,
    )
    .tuya_enum(
        dp_id=12,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
        entity_type=EntityType.CONFIG,
    )
    .tuya_switch(
        dp_id=13,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
        entity_type=EntityType.CONFIG,
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="frequency",
        type=t.uint32_t,
        divisor=1,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.FREQUENCY,
        unit=UnitOfFrequency.HERTZ,
        translation_key="frequency",
        fallback_name="Frequency",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="current",
        type=t.uint32_t,
        divisor=100,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="current",
        fallback_name="Current",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .tuya_sensor(
        dp_id=103,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        translation_key="voltage",
        fallback_name="Voltage",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .tuya_sensor(
        dp_id=104,
        attribute_name="power",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        translation_key="power",
        fallback_name="Power",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .skip_configuration()
    .add_to_registry()
)
