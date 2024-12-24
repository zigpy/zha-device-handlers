"""Tuya TS0601 Thermostat."""

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
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster


class RegulatorPeriod(t.enum8):
    """Tuya Regulator Period enum."""

    FifteenMin = 0x00
    ThirtyMin = 0x01
    FortyFiveMin = 0x02
    SixtyMin = 0x03
    NinetyMin = 0x04


class ThermostatMode(t.enum8):
    """Tuya Thermostat mode."""

    Regulator = 0x00
    Thermostat = 0x01


class PresetMode(t.enum8):
    """Tuya PresetMode enum."""

    Manual = 0x00
    Home = 0x01
    Away = 0x02


class SensorMode(t.enum8):
    """Tuya SensorMode enum."""

    Air = 0x00
    Floor = 0x01
    Both = 0x02


class TuyaThermostat(Thermostat, TuyaAttributesCluster):
    """Tuya local thermostat cluster."""

    manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID

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


(
    TuyaQuirkBuilder("_TZE204_p3lqqy2r", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: 0x00 if not x else 0x04,
        dp_converter=lambda x: x != 0x00,
    )
    .tuya_enum(
        dp_id=2,
        attribute_name="preset_mode",
        enum_class=PresetMode,
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
    .tuya_dp(
        dp_id=28,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=Thermostat.AttributeDefs.local_temperature_calibration.name,
        converter=lambda x: x * 100,
        dp_converter=lambda x: x // 100,
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
        converter=lambda x: 0x00 if not x else 0x01,
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
