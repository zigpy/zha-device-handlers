"""Tuya TS0601 Thermostat."""

from typing import ClassVar

from zigpy.profiles import zha
from zigpy.types import t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
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

    class ServerCommandDefs(TuyaMCUCluster.ServerCommandDefs):
        """Server command definitions."""

        set_time = foundation.ZCLCommandDef(
            id=TUYA_SET_TIME,
            schema={"time": TuyaTimePayload},
            is_manufacturer_specific=False,
        )

    def handle_mcu_version_response(
        self,
        payload: TuyaMCUCluster.MCUVersion,  # type:ignore[valid-type]
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
    .applies_to("_TZE204_gops3slb", "TS0601")
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
    TuyaQuirkBuilder()
    .applies_to("_TZE204_cvub6xbb", "TS0601")
    .applies_to("_TZE284_cvub6xbb", "TS0601")
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


class MoesZhtsrWorkMode(t.enum8):
    """DP 2 - Work mode."""

    Manual = 0x00
    Temporary_Manual = 0x01
    Programming = 0x02
    Energy_Saving = 0x03


class MoesZhtsrSensorChoose(t.enum8):
    """DP 32 - Sensor selection."""

    In = 0x00
    All = 0x01
    Out = 0x02


class MoesZhtsrValveState(t.enum8):
    """DP 47 - Valve state."""

    Close = 0x00
    Open = 0x01


class MoesZhtsrScreenTime(t.enum8):
    """DP 114 - Screen timeout."""

    Ten_S = 0x00
    Twenty_S = 0x01
    Thirty_S = 0x02
    Forty_S = 0x03
    Fifty_S = 0x04
    Sixty_S = 0x05


class MoesZhtsrThermostat(Thermostat, TuyaAttributesCluster):
    """Local thermostat cluster with sane heating-only limits.

    Subclassing TuyaAttributesCluster (not TuyaThermostatCluster) is the v2
    pattern: TuyaThermostatCluster requires a ``thermostat_bus`` that only the
    v1 ``TuyaThermostat`` device class creates, and v2 quirks do not use it.
    """

    _CONSTANT_ATTRIBUTES: ClassVar[dict[int, int]] = {
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 4500,
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        ),
    }


# ---------------------------------------------------------------------------
# Quirk definition
# ---------------------------------------------------------------------------
(
    TuyaQuirkBuilder("_TZE204_lpedvtvr", "TS0601")
    # The device reports device_type 0x0051 (Smart Plug); force thermostat.
    .replaces_endpoint(1, device_type=zha.DeviceType.THERMOSTAT)
    # DP 1 - power switch
    .tuya_onoff(dp_id=1)
    # DP 2 - work mode
    .tuya_enum(
        dp_id=2,
        attribute_name="work_mode",
        enum_class=MoesZhtsrWorkMode,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        translation_key="work_mode",
        fallback_name="Work mode",
    )
    # DP 16 - current temperature (0-900, 1/10 degC)
    .tuya_temperature(dp_id=16, scale=10)
    # DP 50 - target temperature (50-450, 1/10 degC)
    .tuya_number(
        dp_id=50,
        attribute_name="temp_set",
        type=t.uint16_t,
        min_value=5,
        max_value=45,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="temp_set",
        fallback_name="Target temperature",
    )
    # DP 18 - minimum temperature (50-150, 1/10 degC)
    .tuya_number(
        dp_id=18,
        attribute_name="lower_temp",
        type=t.uint16_t,
        min_value=5,
        max_value=15,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="lower_temp",
        fallback_name="Minimum temperature",
    )
    # DP 34 - maximum temperature (350-450, 1/10 degC)
    .tuya_number(
        dp_id=34,
        attribute_name="upper_temp",
        type=t.uint16_t,
        min_value=35,
        max_value=45,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="upper_temp",
        fallback_name="Maximum temperature",
    )
    # DP 101 - temperature calibration (-10..10 degC, 1/10)
    # NOTE: must be int32s, not int16s. ``TuyaData.payload`` decodes every
    # TuyaDPType.VALUE datapoint as ``t.int32s_be`` regardless of the type
    # declared here, so a narrower type makes incoming reports raise
    # ValueError and silently drop the update.
    .tuya_number(
        dp_id=101,
        attribute_name="temp_calibration",
        type=t.int32s,
        min_value=-10,
        max_value=10,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="temp_calibration",
        fallback_name="Temperature calibration",
    )
    # DP 110 - dead zone temperature (5-50, 1/10 degC)
    .tuya_number(
        dp_id=110,
        attribute_name="deadzone_temp",
        type=t.uint16_t,
        min_value=0.5,
        max_value=5,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="deadzone_temp",
        fallback_name="Dead zone temperature",
    )
    # DP 113 - eco temperature (100-300, 1/10 degC)
    .tuya_number(
        dp_id=113,
        attribute_name="eco_temp",
        type=t.uint16_t,
        min_value=10,
        max_value=30,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="eco_temp",
        fallback_name="Eco temperature",
    )
    # DP 111 - high temperature protection (100-700, 1/10 degC)
    .tuya_number(
        dp_id=111,
        attribute_name="high_protect_temp",
        type=t.uint16_t,
        min_value=10,
        max_value=70,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="high_protect_temp",
        fallback_name="High temperature protection",
    )
    # DP 112 - low temperature protection (0-100, 1/10 degC)
    .tuya_number(
        dp_id=112,
        attribute_name="low_protect_temp",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.1,
        translation_key="low_protect_temp",
        fallback_name="Low temperature protection",
    )
    # DP 109 - floor temperature (0-900, 1/10 degC, read only)
    .tuya_sensor(
        dp_id=109,
        attribute_name="floor_temp",
        type=t.uint16_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="floor_temp",
        fallback_name="Floor temperature",
    )
    # DP 47 - valve state (read only)
    .tuya_enum(
        dp_id=47,
        attribute_name="valve_state",
        enum_class=MoesZhtsrValveState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="valve_state",
        fallback_name="Valve state",
    )
    # DP 39 - child lock
    .tuya_switch(
        dp_id=39,
        attribute_name="child_lock",
        entity_type=EntityType.CONFIG,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # DP 32 - sensor selection
    .tuya_enum(
        dp_id=32,
        attribute_name="sensor_choose",
        enum_class=MoesZhtsrSensorChoose,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        translation_key="sensor_choose",
        fallback_name="Sensor selection",
    )
    # DP 48 - backlight brightness (0-100 %)
    .tuya_number(
        dp_id=48,
        attribute_name="backlight",
        type=t.uint8_t,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="backlight",
        fallback_name="Backlight brightness",
    )
    # DP 114 - screen timeout
    .tuya_enum(
        dp_id=114,
        attribute_name="screen_time",
        enum_class=MoesZhtsrScreenTime,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.CONFIG,
        translation_key="screen_time",
        fallback_name="Screen timeout",
    )
    # DP 115 - RGB ambient light
    .tuya_switch(
        dp_id=115,
        attribute_name="rgb_light",
        entity_type=EntityType.CONFIG,
        translation_key="rgb_light",
        fallback_name="RGB ambient light",
    )
    # Local thermostat cluster with heating-only limits
    .adds(MoesZhtsrThermostat)
    .skip_configuration()
    .add_to_registry()
)
