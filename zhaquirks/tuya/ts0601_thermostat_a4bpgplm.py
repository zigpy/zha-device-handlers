"""ZHA custom quirk for Tuya TS0601 radiator thermostat.

Manufacturer: _TZE200_a4bpgplm (and siblings), model TS0601.
z2m model: TS0601_thermostat_1 ("Thermostatic radiator valve").
whiteLabel: id3 GTZ06, AVATTO TRV07.

Datapoint map taken from zigbee-herdsman-converters devices/tuya.ts.
DP1 semantics (thermostatSystemModeAndPreset), raw value:
    0 = auto (schedule), 1 = manual, 2 = off, 3 = on (valve forced open).
Temperatures on the Tuya side are degC*10; the ZCL Thermostat cluster
expects degC*100, hence the *10 / //10 converters.
"""

import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster


class ThermostatTRV(Thermostat, TuyaAttributesCluster):
    """Heating-only radiator thermostat, 5-35 degC setpoint range."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 3500,
        Thermostat.AttributeDefs.min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.max_heat_setpoint_limit.id: 3500,
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        ),
    }

    def __init__(self, *args, **kwargs):
        """Mark standard thermostat attributes the device never reports."""
        super().__init__(*args, **kwargs)
        for attr in (
            Thermostat.AttributeDefs.pi_heating_demand.id,
            Thermostat.AttributeDefs.setpoint_change_source.id,
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id,
            Thermostat.AttributeDefs.setpoint_change_amount.id,
        ):
            self.add_unsupported_attribute(attr)


class ScreenOrientation(t.enum8):
    """DP116 screen orientation."""

    up = 0
    down = 2


class DisplayBrightness(t.enum8):
    """DP152 display brightness."""

    high = 0
    middle = 1
    low = 2


class HysteresisMode(t.enum8):
    """DP153 hysteresis mode."""

    comfort = 0
    eco = 1


class TuyaSystemMode(t.enum8):
    """Raw DP1 values (Tuya enum): combined system_mode/preset."""

    auto = 0  # schedule
    manual = 1  # follow setpoint
    off = 2  # valve closed
    on = 3  # valve forced open


# DP1 (Tuya) <-> ZCL Thermostat.SystemMode.
# The write value MUST be a t.enum8 member so the Tuya MCU serializes it as an
# ENUM datapoint (type 0x04); a plain int would be sent as a 4-byte VALUE and
# the device silently ignores the mode change (e.g. Off would not close).
_TUYA_TO_SYSMODE = {
    TuyaSystemMode.auto: Thermostat.SystemMode.Auto,
    TuyaSystemMode.manual: Thermostat.SystemMode.Heat,
    TuyaSystemMode.off: Thermostat.SystemMode.Off,
    TuyaSystemMode.on: Thermostat.SystemMode.Heat,
}
_SYSMODE_TO_TUYA = {
    Thermostat.SystemMode.Auto: TuyaSystemMode.auto,
    Thermostat.SystemMode.Heat: TuyaSystemMode.manual,
    Thermostat.SystemMode.Off: TuyaSystemMode.off,
}


(
    TuyaQuirkBuilder("_TZE200_a4bpgplm", "TS0601")
    .applies_to("_TZE200_dv8abrrz", "TS0601")
    .applies_to("_TZE200_z1tyspqw", "TS0601")
    .applies_to("_TZE200_bvrlmajk", "TS0601")
    # ----- climate (Thermostat cluster) -----
    .tuya_dp(
        dp_id=1,
        ep_attribute=ThermostatTRV.ep_attribute,
        attribute_name=ThermostatTRV.AttributeDefs.system_mode.name,
        converter=lambda x: _TUYA_TO_SYSMODE.get(x, Thermostat.SystemMode.Heat),
        dp_converter=lambda x: _SYSMODE_TO_TUYA.get(x, TuyaSystemMode.manual),
    )
    .tuya_dp(
        dp_id=2,
        ep_attribute=ThermostatTRV.ep_attribute,
        attribute_name=ThermostatTRV.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=ThermostatTRV.ep_attribute,
        attribute_name=ThermostatTRV.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_dp(
        dp_id=6,
        ep_attribute=ThermostatTRV.ep_attribute,
        attribute_name=ThermostatTRV.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    # ----- switches -----
    .tuya_switch(
        dp_id=4,
        attribute_name="boost_heating",
        translation_key="boost_heating",
        fallback_name="Boost heating",
    )
    .tuya_switch(
        dp_id=8,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_switch(
        dp_id=12,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # ----- numbers -----
    .tuya_number(
        dp_id=5,
        type=t.uint16_t,
        attribute_name="boost_time",
        min_value=0,
        max_value=1000,
        step=1,
        unit="min",
        translation_key="boost_time",
        fallback_name="Boost time",
    )
    .tuya_number(
        dp_id=15,
        type=t.uint16_t,
        attribute_name="min_temperature",
        min_value=1,
        max_value=15,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="min_temperature",
        fallback_name="Min temperature",
    )
    .tuya_number(
        dp_id=16,
        type=t.uint16_t,
        attribute_name="max_temperature",
        min_value=15,
        max_value=35,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_temperature",
        fallback_name="Max temperature",
    )
    .tuya_number(
        dp_id=154,
        type=t.uint16_t,
        attribute_name="switch_deviation_eco",
        min_value=0.5,
        max_value=5.0,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="switch_deviation_eco",
        fallback_name="Eco switch deviation",
    )
    # ----- sensors -----
    .tuya_sensor(
        dp_id=102,
        type=t.uint16_t,
        attribute_name="valve_position",
        divisor=10,
        unit="%",
        entity_type=EntityType.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="valve_position",
        fallback_name="Valve position",
    )
    .tuya_battery(dp_id=13)
    # ----- binary sensors -----
    .tuya_binary_sensor(
        dp_id=7,
        attribute_name="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open",
        fallback_name="Window open",
    )
    .tuya_binary_sensor(
        dp_id=14,
        attribute_name="error_state",
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="error_state",
        fallback_name="Error",
    )
    # ----- selects (enums) -----
    .tuya_enum(
        dp_id=116,
        attribute_name="screen_orientation",
        enum_class=ScreenOrientation,
        translation_key="screen_orientation",
        fallback_name="Screen orientation",
    )
    .tuya_enum(
        dp_id=152,
        attribute_name="display_brightness",
        enum_class=DisplayBrightness,
        translation_key="display_brightness",
        fallback_name="Display brightness",
    )
    .tuya_enum(
        dp_id=153,
        attribute_name="hysteresis_mode",
        enum_class=HysteresisMode,
        translation_key="hysteresis_mode",
        fallback_name="Hysteresis mode",
    )
    .adds(ThermostatTRV)
    .skip_configuration()
    .add_to_registry()
)
