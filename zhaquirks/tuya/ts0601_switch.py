"""Tuya DP-based switches."""

import zigpy.types as t

from zhaquirks.builder import (
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from zhaquirks.tuya import PowerOnState
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import MoesBacklight

# 1 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_7tdtqgwv", "TS0601")
    .applies_to("_TZE200_amp6tsvy", "TS0601")
    .applies_to("_TZE200_oisqyl4o", "TS0601")
    .applies_to("_TZ3000_uim07oem", "TS0601")
    .applies_to("_TZE200_wfxuhoea", "TS0601")
    .applies_to("_TZE200_tviaymwx", "TS0601")
    .applies_to("_TZE204_ptaqh9tk", "TS0601")
    .applies_to("_TZE200_d0ypnbvn", "TS0601")
    .applies_to("_TZE204_6fk3gewc", "TS0601")
    .applies_to("_TZE204_d0ypnbvn", "TS0601")
    .applies_to("_TZE204_v5xjyphj", "TS0601")
    .applies_to("_TZE204_gbagoilo", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch",
        translation_key="switch",
        fallback_name="Switch",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 1 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE200_gbagoilo", "TS0601")
    .applies_to("_TZE284_xnwxmj8z", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch",
        translation_key="switch",
        fallback_name="Switch",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .tuya_sensor(
        dp_id=21,
        attribute_name="current",
        type=t.uint32_t,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="current",
        fallback_name="Current",
    )
    .tuya_sensor(
        dp_id=22,
        attribute_name="power",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        translation_key="power",
        fallback_name="Power",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        translation_key="voltage",
        fallback_name="Voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 2 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_g1ib5ldv", "TS0601")
    .applies_to("_TZE200_wunufsil", "TS0601")
    .applies_to("_TZE200_nkjintbl", "TS0601")
    .applies_to("_TZE204_wvovwe9h", "TS0601")
    .applies_to("_TZE200_7deq70b8", "TS0601")
    .applies_to("_TZE204_nh9m9emk", "TS0601")
    .applies_to("_TZE200_wvovwe9h", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 2 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE200_nh9m9emk", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .tuya_sensor(
        dp_id=21,
        attribute_name="current",
        type=t.uint32_t,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="current",
        fallback_name="Current",
    )
    .tuya_sensor(
        dp_id=22,
        attribute_name="power",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        translation_key="power",
        fallback_name="Power",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        translation_key="voltage",
        fallback_name="Voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 3 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_tz32mtza", "TS0601")
    .applies_to("_TZE200_vhy3iakz", "TS0601")
    .applies_to("_TZE200_2hf7x9n3", "TS0601")
    .applies_to("_TZE200_kyfqmmyl", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 3 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE204_2imwyigp", "TS0601")
    .applies_to("_TZE200_2imwyigp", "TS0601")
    .applies_to("_TZE200_go3tvswy", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .tuya_sensor(
        dp_id=21,
        attribute_name="current",
        type=t.uint32_t,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="current",
        fallback_name="Current",
    )
    .tuya_sensor(
        dp_id=22,
        attribute_name="power",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        translation_key="power",
        fallback_name="Power",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        translation_key="voltage",
        fallback_name="Voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 4 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_aqnazj70", "TS0601")
    .applies_to("_TZE200_1ozguk6x", "TS0601")
    .applies_to("_TZE200_k6jhsr0q", "TS0601")
    .applies_to("_TZE200_1n2kyphz", "TS0601")
    .applies_to("_TZE200_mexisfik", "TS0601")
    .applies_to("_TZE204_58of2pfn", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 4 Gang Switch with Power Meter
(
    TuyaQuirkBuilder("_TZE204_mexisfik", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        translation_key="backlight_switch",
        fallback_name="Backlight switch",
    )
    .tuya_sensor(
        dp_id=21,
        attribute_name="current",
        type=t.uint32_t,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="current",
        fallback_name="Current",
    )
    .tuya_sensor(
        dp_id=22,
        attribute_name="power",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        translation_key="power",
        fallback_name="Power",
    )
    .tuya_sensor(
        dp_id=23,
        attribute_name="voltage",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        translation_key="voltage",
        fallback_name="Voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# 5 Gang Moes Switch
(
    TuyaQuirkBuilder("_TZE200_jwsjbxjs", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_5",
        translation_key="switch_5",
        fallback_name="Switch 5",
        entity_type=EntityType.STANDARD,
    )
    .tuya_enum(
        dp_id=14,
        enum_class=PowerOnState,
        attribute_name="power_on_state",
        translation_key="power_on_state",
        fallback_name="Power-on state",
    )
    .tuya_enum(
        dp_id=15,
        enum_class=MoesBacklight,
        attribute_name="backlight_mode",
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .skip_configuration()
    .add_to_registry()
)

# 5 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE200_leaqthqq", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_5",
        translation_key="switch_5",
        fallback_name="Switch 5",
        entity_type=EntityType.STANDARD,
    )
    .skip_configuration()
    .add_to_registry()
)

# 6 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE200_9mahtqtg", "TS0601")
    .applies_to("_TZE200_wnp4d4va", "TS0601")
    .applies_to("_TZE200_emxxanvi", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_5",
        translation_key="switch_5",
        fallback_name="Switch 5",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=6,
        attribute_name="switch_6",
        translation_key="switch_6",
        fallback_name="Switch 6",
        entity_type=EntityType.STANDARD,
    )
    .skip_configuration()
    .add_to_registry()
)

# 8 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE200_wktrysab", "TS0601")
    .applies_to("_TZE204_wktrysab", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_5",
        translation_key="switch_5",
        fallback_name="Switch 5",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=6,
        attribute_name="switch_6",
        translation_key="switch_6",
        fallback_name="Switch 6",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x65,
        attribute_name="switch_7",
        translation_key="switch_7",
        fallback_name="Switch 7",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x66,
        attribute_name="switch_8",
        translation_key="switch_8",
        fallback_name="Switch 8",
        entity_type=EntityType.STANDARD,
    )
    .skip_configuration()
    .add_to_registry()
)

# 12 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE204_dqolcpcp", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_5",
        translation_key="switch_5",
        fallback_name="Switch 5",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=6,
        attribute_name="switch_6",
        translation_key="switch_6",
        fallback_name="Switch 6",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x65,
        attribute_name="switch_7",
        translation_key="switch_7",
        fallback_name="Switch 7",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x66,
        attribute_name="switch_8",
        translation_key="switch_8",
        fallback_name="Switch 8",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x67,
        attribute_name="switch_9",
        translation_key="switch_9",
        fallback_name="Switch 9",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x68,
        attribute_name="switch_10",
        translation_key="switch_10",
        fallback_name="Switch 10",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x69,
        attribute_name="switch_11",
        translation_key="switch_11",
        fallback_name="Switch 11",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x6A,
        attribute_name="switch_12",
        translation_key="switch_12",
        fallback_name="Switch 12",
        entity_type=EntityType.STANDARD,
    )
    .skip_configuration()
    .add_to_registry()
)

# 16 Gang Standard Switch
(
    TuyaQuirkBuilder("_TZE204_vmcgja59", "TS0601")
    .tuya_switch(
        dp_id=1,
        attribute_name="switch_1",
        translation_key="switch_1",
        fallback_name="Switch 1",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="switch_2",
        translation_key="switch_2",
        fallback_name="Switch 2",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=3,
        attribute_name="switch_3",
        translation_key="switch_3",
        fallback_name="Switch 3",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=4,
        attribute_name="switch_4",
        translation_key="switch_4",
        fallback_name="Switch 4",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=5,
        attribute_name="switch_5",
        translation_key="switch_5",
        fallback_name="Switch 5",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=6,
        attribute_name="switch_6",
        translation_key="switch_6",
        fallback_name="Switch 6",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x65,
        attribute_name="switch_7",
        translation_key="switch_7",
        fallback_name="Switch 7",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x66,
        attribute_name="switch_8",
        translation_key="switch_8",
        fallback_name="Switch 8",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x67,
        attribute_name="switch_9",
        translation_key="switch_9",
        fallback_name="Switch 9",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x68,
        attribute_name="switch_10",
        translation_key="switch_10",
        fallback_name="Switch 10",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x69,
        attribute_name="switch_11",
        translation_key="switch_11",
        fallback_name="Switch 11",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x6A,
        attribute_name="switch_12",
        translation_key="switch_12",
        fallback_name="Switch 12",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x6B,
        attribute_name="switch_13",
        translation_key="switch_13",
        fallback_name="Switch 13",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x6C,
        attribute_name="switch_14",
        translation_key="switch_14",
        fallback_name="Switch 14",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x6D,
        attribute_name="switch_15",
        translation_key="switch_15",
        fallback_name="Switch 15",
        entity_type=EntityType.STANDARD,
    )
    .tuya_switch(
        dp_id=0x6E,
        attribute_name="switch_16",
        translation_key="switch_16",
        fallback_name="Switch 16",
        entity_type=EntityType.STANDARD,
    )
    .skip_configuration()
    .add_to_registry()
)
