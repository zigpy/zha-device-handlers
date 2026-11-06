"""Sonoff TRVZB - Zigbee Thermostatic Radiator Valve."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import (
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

"""SONOFF CustomCluster specific thermostat attribute ids."""
SONOFF_MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC11

# Child Lock, Attribute ID 0x0000, Bool
SONOFF_CHILD_LOCK_ATTR_ID = 0x0000
# 0x00=False (TRV can be operated)
# 0x01=True (TRV operation blocked)

# Display Orientation, Screen Rotation, Attribute ID 0x0021, uint8
SONOFF_DISPLAY_ORIENTATION_ATTR_ID = 0x0021
# 0x00=Horizontal (default) - 0° rotate, named horizontal in eWeLink
# 0x01=Rotate 90° - 90° rotate, on TRV-ZBT
# 0x02=Vertical (flipped) - 180° rotate, named vertical in eWeLink
# 0x03=Rotate 270° - 270° rotate, on TRV-ZBT

# Open Window Detection, Attribute 0x6000, Bool
SONOFF_OPEN_WINDOW_DETECTION_ATTR_ID = 0x6000
# 0x00=False
# 0x01=True (temperature drop of >1.5°C in 4.5 minutes, target temperature 12°C)

# Anti Freeze Temperature, Attribute ID 0x6002, int16
SONOFF_ANTI_FREEZE_TEMPERATURE_ATTR_ID = 0x6002
# 700=7.0°C temperature in 1/100th degree celsius

# Idle Steps, Attribute ID 0x6003, uint16
SONOFF_IDLE_STEPS_ATTR_ID = 0x6003

# Closing Steps, Attribute ID 0x6004, uint16
SONOFF_CLOSING_STEPS_ATTR_ID = 0x6004

# Valve Opening Limit Voltage, Attribute ID 0x6005, uint16
SONOFF_OPENING_LIMIT_VOLTAGE_ATTR_ID = 0x6005

# Valve Closing Limit Voltage, Attribute ID 0x6006, uint16
SONOFF_CLOSING_LIMIT_VOLTAGE_ATTR_ID = 0x6006

# Valve Motor Running Voltage, Attribute ID 0x6007, int16
SONOFF_VALVE_RUNNING_VOLTAGE_ATTR_ID = 0x6007

# Normal Mode Heating Set Point, Attribute ID 0x6009, int16
SONOFF_REGULAR_HEATING_SETPOINT_ATTR_ID = 0x6009
# in 1/100th degree celsius (1550=15.5°C, 2000=20.0°C)

# Auto Mode Heating Set Point, Attribute ID 0x600a, int16
SONOFF_AUTOMODE_HEATING_SETPOINT_ATTR_ID = 0x600A
# in 1/100th degree celsius (1550=15.5°C, 2000=20.0°C)

# Valve Opening Percentage, Attribute ID 0x600b, uint8
SONOFF_VALVE_OPENING_PERCENTAGE_ATTR_ID = 0x600B
# in percent 0x64=100=100%

# Valve Closing Percentage, Attribute ID 0x600c, uint8
SONOFF_VALVE_CLOSING_PERCENTAGE_ATTR_ID = 0x600C
# in percent 0x64=100=100%

# External Temperature Sensor Value, Attribute ID 0x600D, int16
SONOFF_EXTERNAL_TEMP_SENSOR_VALUE_ATTR_ID = 0x600D
# temperature in 1/100th °C degree celsius
# ONLY used if External Temperature Sensor Enable is active
# ONLY valid for 120 minutes after writing, then becomes ignored if not changed

# External Temperature Sensor Enable, Attribute ID 0x600e, uint8
SONOFF_EXTERNAL_TEMP_SENSOR_ENABLE_ATTR_ID = 0x600E

# Temperature Accuracy Adjust, Attribute ID 0x6011
SONOFF_TEMPERATURE_ACCURACY_ADJUST_ATTR_ID = 0x6011
# in 1/100th degree celsius, (-100=-1.0°C), cut to 1/10th degree celsius
# not, if Adaptive Mode is activated

# Temperature Control Mode (Adaptive Mode on TRV-ZBT), Attribute ID 0x6013, enum8
SONOFF_TEMPERATURE_CONTROL_MODE_ATTR_ID = 0x6013
# 0x01=Manual
# 0x02=Adaptive Mode

# Temporary Activation Mode, Attribute ID 0x6014, uint8
SONOFF_TEMPORARY_ACTIVATION_MODE_ATTR_ID = 0x6014
# 0x00=Boost (set 0x6015 activation time first)
# 0x01=Scheduled (set 0x6015 activation time and 0x6016 temperature first)

# Temporary Activation Duration, Attribute ID 0x6015, uint32
SONOFF_TEMPORARY_ACTIVATION_DURATION_ATTR_ID = 0x6015
# activation duration in seconds (900=15 minutes)

# Temporary Target Temperature, Attribute ID 0x6016, int16
SONOFF_TEMPORARY_TARGET_TEMPERATURE_ATTR_ID = 0x6016
# 500=5.0°C temperature in 1/100th degree celsius

# Smart Mode (TRVZB adaptive mode), Attribute ID 0x6017, enum8
SONOFF_SMART_TEMPERATURE_CONTROL_ATTR_ID = 0x6017
# 0x00=Inactive (Valve opening percentage and temperature accuracy possible)
# 0x02=Active (Valve opening based on target temperature and temperature changes)


class SonoffDisplayOrientation(t.enum8):
    """Rotation of display orientation."""

    # 4-way rotation values for TRV-ZBT, TRVZB only has 2-way flipp
    Rotate_0 = 0x00  # Rotate 0°, default orientation, named Horizontal in eWeLink
    Rotate_90 = 0x01  # Rotate 90°, on TRVZB reports back 0°
    Rotate_180 = 0x02  # Rotate 180°, named Vertical in eWeLink
    Rotate_270 = 0x03  # Rotate 270°, on TRVZB reports back 180°


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = SONOFF_MANUFACTURER_SPECIFIC_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        child_lock = ZCLAttributeDef(
            id=SONOFF_CHILD_LOCK_ATTR_ID,
            type=t.Bool,
            manufacturer_code=None,
        )
        display_orientation = ZCLAttributeDef(
            id=SONOFF_DISPLAY_ORIENTATION_ATTR_ID,
            type=SonoffDisplayOrientation,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=None,
        )
        open_window = ZCLAttributeDef(
            id=SONOFF_OPEN_WINDOW_DETECTION_ATTR_ID,
            type=t.Bool,
            manufacturer_code=None,
        )
        frost_protection_temperature = ZCLAttributeDef(
            id=SONOFF_ANTI_FREEZE_TEMPERATURE_ATTR_ID,
            type=t.int16s,
            manufacturer_code=None,
        )
        idle_steps = ZCLAttributeDef(
            id=SONOFF_IDLE_STEPS_ATTR_ID,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        closing_steps = ZCLAttributeDef(
            id=SONOFF_CLOSING_STEPS_ATTR_ID,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        valve_opening_limit_voltage = ZCLAttributeDef(
            id=SONOFF_OPENING_LIMIT_VOLTAGE_ATTR_ID,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        valve_closing_limit_voltage = ZCLAttributeDef(
            id=SONOFF_CLOSING_LIMIT_VOLTAGE_ATTR_ID,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        valve_motor_running_voltage = ZCLAttributeDef(
            id=SONOFF_VALVE_RUNNING_VOLTAGE_ATTR_ID,
            type=t.uint16_t,
            access="r",
            manufacturer_code=None,
        )
        regular_heating_setpoint = ZCLAttributeDef(
            id=SONOFF_REGULAR_HEATING_SETPOINT_ATTR_ID,
            type=t.int16s,
            manufacturer_code=None,
        )
        automode_heating_setpoint = ZCLAttributeDef(
            id=SONOFF_AUTOMODE_HEATING_SETPOINT_ATTR_ID,
            type=t.int16s,
            manufacturer_code=None,
        )
        valve_opening_degree = ZCLAttributeDef(
            id=SONOFF_VALVE_OPENING_PERCENTAGE_ATTR_ID,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        valve_closing_degree = ZCLAttributeDef(
            id=SONOFF_VALVE_CLOSING_PERCENTAGE_ATTR_ID,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        external_temperature_sensor_enable = ZCLAttributeDef(
            id=SONOFF_EXTERNAL_TEMP_SENSOR_ENABLE_ATTR_ID,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        external_temperature_sensor_value = ZCLAttributeDef(
            id=SONOFF_EXTERNAL_TEMP_SENSOR_VALUE_ATTR_ID,
            type=t.int16s,
            manufacturer_code=None,
        )
        temperature_control_accuracy = ZCLAttributeDef(
            id=SONOFF_TEMPERATURE_ACCURACY_ADJUST_ATTR_ID,
            type=t.int16s,
            manufacturer_code=None,
        )
        temporary_mode = ZCLAttributeDef(
            id=SONOFF_TEMPORARY_ACTIVATION_MODE_ATTR_ID,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        temporary_mode_duration = ZCLAttributeDef(
            id=SONOFF_TEMPORARY_ACTIVATION_DURATION_ATTR_ID,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        timer_mode_target_temperature = ZCLAttributeDef(
            id=SONOFF_TEMPORARY_TARGET_TEMPERATURE_ATTR_ID,
            type=t.int16s,
            manufacturer_code=None,
        )
        smart_temperature_control = ZCLAttributeDef(
            id=SONOFF_SMART_TEMPERATURE_CONTROL_ATTR_ID,
            type=t.bitmap8,
            manufacturer_code=None,
        )
        # TRV-ZBT only: adaptive control lives here instead of 0x6017
        temperature_control_mode = ZCLAttributeDef(
            id=SONOFF_TEMPERATURE_CONTROL_MODE_ATTR_ID,
            type=t.enum8,
            manufacturer_code=None,
        )


BASE_TRVZB_QUIRK = (
    QuirkBuilder()
    .replaces(CustomSonoffCluster)
    .switch(
        CustomSonoffCluster.AttributeDefs.child_lock.name,
        CustomSonoffCluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.open_window.name,
        CustomSonoffCluster.cluster_id,
        translation_key="open_window",
        fallback_name="Open window",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temporary_mode_duration.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=1440,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        multiplier=1 / 60,
        translation_key="temporary_mode_duration",
        fallback_name="Temporary mode duration",
    )
    .write_attr_button(
        attribute_name=CustomSonoffCluster.AttributeDefs.temporary_mode.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        attribute_value=0x00,
        unique_id_suffix="boost_mode",
        translation_key="boost_mode",
        fallback_name="Boost mode",
    )
    .write_attr_button(
        attribute_name=CustomSonoffCluster.AttributeDefs.temporary_mode.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        attribute_value=0x01,
        unique_id_suffix="timer_mode",
        translation_key="timer_mode",
        fallback_name="Timer mode",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.valve_opening_degree.name,
        CustomSonoffCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        translation_key="valve_opening_degree",
        fallback_name="Valve opening degree",
        initially_disabled=True,
    )
    .number(
        CustomSonoffCluster.AttributeDefs.valve_closing_degree.name,
        CustomSonoffCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        translation_key="valve_closing_degree",
        fallback_name="Valve closing degree",
        initially_disabled=True,
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_control_accuracy.name,
        CustomSonoffCluster.cluster_id,
        min_value=-1.0,
        max_value=-0.2,
        step=0.2,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_control_accuracy",
        fallback_name="Temperature control accuracy",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.external_temperature_sensor_enable.name,
        CustomSonoffCluster.cluster_id,
        translation_key="external_temperature_sensor",
        fallback_name="External temperature sensor",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.external_temperature_sensor_value.name,
        CustomSonoffCluster.cluster_id,
        min_value=0.0,
        max_value=99.9,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="external_temperature_sensor_value",
        fallback_name="External temperature sensor value",
    )
    .enum(
        attribute_name=CustomSonoffCluster.AttributeDefs.display_orientation.name,
        enum_class=SonoffDisplayOrientation,
        cluster_id=CustomSonoffCluster.cluster_id,
        translation_key="display_orientation",
        fallback_name="Display Orientation",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.regular_heating_setpoint.name,
        CustomSonoffCluster.cluster_id,
        min_value=4.0,
        max_value=35.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="regular_heating_setpoint",
        fallback_name="Regular heating setpoint",
        initially_disabled=True,
    )
    .number(
        CustomSonoffCluster.AttributeDefs.automode_heating_setpoint.name,
        CustomSonoffCluster.cluster_id,
        min_value=4.0,
        max_value=35.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="automode_heating_setpoint",
        fallback_name="Auto mode heating setpoint",
        initially_disabled=True,
    )
)

(
    BASE_TRVZB_QUIRK.clone()
    .applies_to("SONOFF", "TRVZB")
    .number(
        CustomSonoffCluster.AttributeDefs.timer_mode_target_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=4.0,
        max_value=35.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="timer_mode_target_temperature",
        fallback_name="Timer mode target temperature",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.frost_protection_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=4.0,
        max_value=35.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.smart_temperature_control.name,
        # ControlModeType,
        CustomSonoffCluster.cluster_id,
        on_value=2,
        off_value=0,
        translation_key="adaptive_mode",
        fallback_name="Adaptive mode",
    )
    .add_to_registry()
)

(
    # The TRV-ZBT has the same 0xFC11 attribute set, except that adaptive
    # control is `temperature_control_mode` (0x6013, enum8, 1 = manual,
    # 2 = adaptive); 0x6017 is unsupported on this model. It also only
    # accepts frost protection from 5 to 15 °C and a timer mode target
    # temperature from 5 to 30 °C; other values are rejected.
    # Further it has 4-way display rotation.
    BASE_TRVZB_QUIRK.clone()
    .applies_to("SONOFF", "TRV-ZBT")
    .number(
        CustomSonoffCluster.AttributeDefs.timer_mode_target_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=5.0,
        max_value=30.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="timer_mode_target_temperature",
        fallback_name="Timer mode target temperature",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.frost_protection_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=5.0,
        max_value=15.0,
        step=0.5,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.temperature_control_mode.name,
        CustomSonoffCluster.cluster_id,
        on_value=2,
        off_value=1,
        translation_key="adaptive_mode",
        fallback_name="Adaptive mode",
    )
    .add_to_registry()
)
