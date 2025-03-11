"""Tuya TS0601 Thermostat."""

import copy

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityType
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.types import t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.tuya import TUYA_SET_TIME, TuyaTimePayload
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster, TuyaMCUCluster


class RegulatorPeriod(t.enum8):
    """Tuya regulator period enum."""

    _15_min = 0x00
    _30_min = 0x01
    _45_min = 0x02
    _60_min = 0x03
    _90_min = 0x04


class ThermostatMode(t.enum8):
    """Tuya thermostat mode."""

    Regulator = 0x00
    Thermostat = 0x01


class PresetModeV01(t.enum8):
    """Tuya preset mode v01 enum."""

    Manual = 0x00
    Home = 0x01
    Away = 0x02


class PresetModeV02(t.enum8):
    """Tuya preset mode v02 enum."""

    Manual = 0x00
    Auto = 0x01
    Temporary_Manual = 0x02


class PresetModeV03(t.enum8):
    """Tuya preset mode v03 enum."""

    Auto = 0x00
    Manual = 0x01
    Temporary_Manual = 0x02


class PresetModeV04(t.enum8):
    """Tuya preset mode v04 enum."""

    Manual = 0x00
    Auto = 0x01
    Eco = 0x03


class SensorMode(t.enum8):
    """Tuya sensor mode enum."""

    Air = 0x00
    Floor = 0x01
    Both = 0x02


class BacklightMode(t.enum8):
    """Tuya backlight mode enum."""

    Off = 0x00
    Low = 0x01
    Medium = 0x02
    High = 0x03


class WorkingDayV01(t.enum8):
    """Tuya Working day v01 enum."""

    Disabled = 0x00
    Six_One = 0x01
    Five_Two = 0x02
    Seven = 0x03


class WorkingDayV02(t.enum8):
    """Tuya Working day v02 enum."""

    Disabled = 0x00
    Five_Two = 0x01
    Six_One = 0x02
    Seven = 0x03


class RunningMode(t.enum8):
    """Tuya running mode enum."""

    Heat = 0x00
    Cool = 0x01


class TuyaThermostat(Thermostat, TuyaAttributesCluster):
    """Tuya local thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    def __init__(self, *args, **kwargs):
        """Init a TuyaThermostat cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id
        )
        self.add_unsupported_attribute(Thermostat.AttributeDefs.pi_heating_demand.id)

        # Previously mapped, marking as explicitly unsupported.
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.local_temperature_calibration.id
        )


class NoManufTimeNoVersionRespTuyaMCUCluster(TuyaMCUCluster):
    """Tuya Manufacturer Cluster with set_time mod."""

    # Deepcopy required to override 'set_time', without, it will revert
    server_commands = copy.deepcopy(TuyaMCUCluster.server_commands)
    server_commands.update(
        {
            TUYA_SET_TIME: foundation.ZCLCommandDef(
                "set_time",
                {"time": TuyaTimePayload},
                False,
                is_manufacturer_specific=False,
            ),
        }
    )

    def handle_mcu_version_response(
        self, payload: TuyaMCUCluster.MCUVersion
    ) -> foundation.Status:
        """Handle MCU version response."""
        return foundation.Status.SUCCESS


(
    TuyaQuirkBuilder("_TZE204_p3lqqy2r", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: {
            True: Thermostat.SystemMode.Heat,
            False: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Heat: True,
            Thermostat.SystemMode.Off: False,
        }[x],
    )
    .tuya_enum(
        dp_id=2,
        attribute_name="preset_mode",
        enum_class=PresetModeV01,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_dp(
        dp_id=16,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 100,
        dp_converter=lambda x: x // 100,
    )
    .tuya_dp(
        dp_id=24,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 100,
    )
    .tuya_number(
        dp_id=28,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-9,
        max_value=9,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_switch(
        dp_id=30,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="local_temperature_floor",
        type=t.int16s,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="local_temperature_floor",
        fallback_name="Floor temperature",
    )
    .tuya_enum(
        dp_id=102,
        attribute_name="temperature_sensor_select",
        enum_class=SensorMode,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    .tuya_dp(
        dp_id=104,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_binary_sensor(
        dp_id=106,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_dp(
        dp_id=107,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.max_heat_setpoint_limit.name,
        converter=lambda x: x * 100,
        dp_converter=lambda x: x // 100,
    )
    .tuya_enum(
        dp_id=108,
        attribute_name="thermostat_mode",
        enum_class=ThermostatMode,
        translation_key="thermostat_mode",
        fallback_name="Thermostat mode",
    )
    .tuya_enum(
        dp_id=109,
        attribute_name="regulator_period",
        enum_class=RegulatorPeriod,
        translation_key="regulator_period",
        fallback_name="Regulator period",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="regulator_set_point",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="regulator_set_point",
        fallback_name="Regulator set point",
    )
    .adds(TuyaThermostat)
    .tuya_sensor(
        dp_id=120,
        attribute_name="current",
        type=t.int16s,
        divisor=10,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current",
    )
    .tuya_sensor(
        dp_id=121,
        attribute_name="voltage",
        type=t.int16s,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage",
    )
    .tuya_sensor(
        dp_id=122,
        attribute_name="power",
        type=t.int16s,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        fallback_name="Power",
    )
    .tuya_sensor(
        dp_id=123,
        attribute_name="energy",
        type=t.int16s,
        divisor=100,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya ZWT198/ZWT100-BH Avatto wall thermostat
base_avatto_quirk = (
    TuyaQuirkBuilder()
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: {
            True: Thermostat.SystemMode.Heat,
            False: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Heat: True,
            Thermostat.SystemMode.Off: False,
        }[x],
    )
    .tuya_dp(
        dp_id=2,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_switch(
        dp_id=9,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_binary_sensor(
        dp_id=11,
        attribute_name="fault_alarm",
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="fault_alarm",
        fallback_name="Fault alarm",
    )
    .tuya_dp(
        dp_id=15,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.max_heat_setpoint_limit.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_number(
        dp_id=19,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-9.9,
        max_value=9.9,
        unit=UnitOfTemperature.CELSIUS,
        step=0.1,
        multiplier=0.1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_switch(
        dp_id=102,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=103,
        attribute_name="factory_reset",
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    .tuya_enum(
        dp_id=106,
        attribute_name="temperature_sensor_select",
        enum_class=SensorMode,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="deadzone_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0.5,
        max_value=10,
        step=0.5,
        multiplier=0.1,
        translation_key="deadzone_temperature",
        fallback_name="Deadzone temperature",
    )
    # 109 ZWT198 schedule, skipped
    .tuya_enum(
        dp_id=110,
        attribute_name="backlight_mode",
        enum_class=BacklightMode,
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .adds(TuyaThermostat)
    .skip_configuration()
)


(
    base_avatto_quirk.clone()
    .applies_to("_TZE204_lzriup1j", "TS0601")
    .tuya_enum(
        dp_id=4,
        attribute_name="preset_mode",
        enum_class=PresetModeV02,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="working_day",
        enum_class=WorkingDayV02,
        translation_key="working_day",
        fallback_name="Working day",
    )
    .add_to_registry(replacement_cluster=NoManufTimeNoVersionRespTuyaMCUCluster)
)


(
    base_avatto_quirk.clone()
    .applies_to("_TZE200_viy9ihs7", "TS0601")
    .tuya_enum(
        dp_id=4,
        attribute_name="preset_mode",
        enum_class=PresetModeV03,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="working_day",
        enum_class=WorkingDayV01,
        translation_key="working_day",
        fallback_name="Working day",
    )
    .add_to_registry(replacement_cluster=NoManufTimeNoVersionRespTuyaMCUCluster)
)


(
    base_avatto_quirk.clone()
    .applies_to("_TZE204_xnbkhhdr", "TS0601")
    .applies_to("_TZE284_xnbkhhdr", "TS0601")
    .tuya_enum(
        dp_id=4,
        attribute_name="preset_mode",
        enum_class=PresetModeV03,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="working_day",
        enum_class=WorkingDayV02,
        translation_key="working_day",
        fallback_name="Working day",
    )
    .add_to_registry(replacement_cluster=NoManufTimeNoVersionRespTuyaMCUCluster)
)


# Beok TGM50-ZB-WPB
(
    TuyaQuirkBuilder("_TZE204_cvub6xbb", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: {
            True: Thermostat.SystemMode.Heat,
            False: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Heat: True,
            Thermostat.SystemMode.Off: False,
        }[x],
    )
    .tuya_dp(
        dp_id=2,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_enum(
        dp_id=4,
        attribute_name="preset_mode",
        enum_class=PresetModeV04,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_switch(
        dp_id=9,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_dp(
        dp_id=15,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.max_heat_setpoint_limit.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_number(
        dp_id=19,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-9.9,
        max_value=9.9,
        unit=UnitOfTemperature.CELSIUS,
        step=0.1,
        multiplier=0.1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_switch(
        dp_id=102,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=103,
        attribute_name="factory_reset",
        translation_key="factory_reset",
        fallback_name="Factory reset",
    )
    .tuya_switch(
        dp_id=105,
        attribute_name="sound_enabled",
        translation_key="sound_enabled",
        fallback_name="Sound enabled",
    )
    .tuya_enum(
        dp_id=106,
        attribute_name="temperature_sensor_select",
        enum_class=SensorMode,
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="deadzone_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0.5,
        max_value=10,
        step=0.5,
        multiplier=0.1,
        translation_key="deadzone_temperature",
        fallback_name="Deadzone temperature",
    )
    # 109 ZWT198 schedule, skipped
    .tuya_enum(
        dp_id=110,
        attribute_name="backlight_mode",
        enum_class=BacklightMode,
        translation_key="backlight_mode",
        fallback_name="Backlight mode",
    )
    .tuya_switch(
        dp_id=111,
        attribute_name="invert_relay",
        on_value=0,
        off_value=1,
        translation_key="invert_relay",
        fallback_name="Invert relay",
    )
    .adds(TuyaThermostat)
    .skip_configuration()
    .add_to_registry()
)

# Tervix Pro Line Zigbee
(
    TuyaQuirkBuilder("_TZE200_6kijc7nd", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: {
            True: Thermostat.SystemMode.Heat,
            False: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Heat: True,
            Thermostat.SystemMode.Off: False,
        }[x],
    )
    .tuya_enum(
        dp_id=2,
        attribute_name="preset_mode",
        enum_class=PresetModeV02,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_binary_sensor(
        dp_id=8,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Window Detection",
    )
    .tuya_binary_sensor(
        dp_id=10,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost Protection",
    )
    .tuya_dp(
        dp_id=16,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_number(
        dp_id=19,
        attribute_name="temperature_ceiling",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=35,
        max_value=95,
        multiplier=0.1,
        step=0.5,
        translation_key="temperature_ceiling",
        fallback_name="Temperature Ceiling",
    )
    .tuya_dp(
        dp_id=24,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_binary_sensor(
        dp_id=25,
        attribute_name="window_state",
        translation_key="window_state",
        fallback_name="Window State",
    )
    .tuya_number(
        dp_id=27,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-9,
        max_value=9,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Temperature Correction",
    )
    .tuya_binary_sensor(
        dp_id=34,
        attribute_name="humidity_display",
        translation_key="humidity_display",
        fallback_name="Humidity Display",
    )
    .tuya_binary_sensor(
        dp_id=39,
        attribute_name="factory_reset",
        translation_key="factory_reset",
        fallback_name="Factory Reset",
    )
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child Lock",
    )
    .tuya_enum(
        dp_id=43,
        attribute_name="sensor_selection",
        enum_class=SensorMode,
        translation_key="sensor_selection",
        fallback_name="Sensor Selection",
    )
    .tuya_enum(
        dp_id=58,
        attribute_name="running_mode",
        enum_class=RunningMode,
        translation_key="running_mode",
        fallback_name="Running Mode (Heat/Cool)",
    )
    .tuya_number(
        dp_id=101,
        attribute_name="switch_sensitivity",
        type=t.uint8_t,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="switch_sensitivity",
        fallback_name="Switch Sensitivity",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="floor_max_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=60,
        multiplier=0.1,
        step=0.5,
        translation_key="floor_max_temperature",
        fallback_name="Floor Maximum Temperature Protection",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="floor_min_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=10,
        max_value=30,
        multiplier=0.1,
        step=0.5,
        translation_key="floor_min_temperature",
        fallback_name="Floor Minimum Temperature",
    )
    .tuya_number(
        dp_id=104,
        attribute_name="open_window_time",
        type=t.uint16_t,
        unit="min",
        min_value=0,
        max_value=60,
        step=1,
        translation_key="open_window_time",
        fallback_name="Open Window Time",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="open_window_temp",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0,
        max_value=30,
        multiplier=0.1,
        step=0.5,
        translation_key="open_window_temp",
        fallback_name="Open Window Temperature",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="open_window_delay_time",
        type=t.uint16_t,
        unit="min",
        min_value=0,
        max_value=60,
        step=1,
        translation_key="open_window_delay_time",
        fallback_name="Open Window Delay Time",
    )
    .tuya_binary_sensor(
        dp_id=107,
        attribute_name="humidity_control",
        translation_key="humidity_control",
        fallback_name="Humidity Control",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="upper_humidity_limit",
        type=t.uint8_t,
        unit="%",
        min_value=0,
        max_value=100,
        step=1,
        translation_key="upper_humidity_limit",
        fallback_name="Upper Humidity Limit",
    )
    .adds(TuyaThermostat)
    .skip_configuration()
    .add_to_registry()
)
