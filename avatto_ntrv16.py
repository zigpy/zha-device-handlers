"""Avatto N-TRV16 thermostatic radiator valve."""

import zigpy.types as t
from zigpy.quirks.v2.homeassistant import UnitOfTemperature
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster


class AvattoPreset(t.enum8):
    """Avatto N-TRV16 preset modes."""

    Manual = 0x00
    Schedule = 0x01
    Eco = 0x02
    Comfort = 0x03
    FrostProtection = 0x04
    Holiday = 0x05
    Off = 0x06


class AvattoNTRV16Thermostat(Thermostat, TuyaAttributesCluster):
    """Avatto N-TRV16 thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,   # 5°C
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 3500,  # 35°C
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        ),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.pi_heating_demand.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.local_temperature_calibration.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.min_heat_setpoint_limit.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.max_heat_setpoint_limit.id
        )


(
    TuyaQuirkBuilder("_TZE204_vjpaih9f", "TS0601")

    # DP5 = local_temperature (current temperature, value x10 in decidegrees)
    .tuya_dp(
        dp_id=5,
        ep_attribute=AvattoNTRV16Thermostat.ep_attribute,
        attribute_name=AvattoNTRV16Thermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )

    # DP4 = occupied_heating_setpoint (target temperature, value x10)
    .tuya_dp(
        dp_id=4,
        ep_attribute=AvattoNTRV16Thermostat.ep_attribute,
        attribute_name=AvattoNTRV16Thermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )

    # DP3 = running_state (heating / idle)
    .tuya_dp(
        dp_id=3,
        ep_attribute=AvattoNTRV16Thermostat.ep_attribute,
        attribute_name=AvattoNTRV16Thermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x == 1 else RunningState.Idle,
    )

    # DP2 = system_mode / preset (0=manual, 1=schedule, 2=eco, 3=comfort, 4=frost, 5=holiday, 6=off)
    .tuya_dp(
        dp_id=2,
        ep_attribute=AvattoNTRV16Thermostat.ep_attribute,
        attribute_name=AvattoNTRV16Thermostat.AttributeDefs.system_mode.name,
        converter=lambda x: (
            Thermostat.SystemMode.Off
            if x == AvattoPreset.Off
            else Thermostat.SystemMode.Heat
        ),
        dp_converter=lambda x: (
            int(AvattoPreset.Off)
            if x == Thermostat.SystemMode.Off
            else int(AvattoPreset.Manual)
        ),
    )

    .adds(AvattoNTRV16Thermostat)

    # DP6 = battery (%)
    .tuya_battery(dp_id=6)

    # DP7 = child_lock
    .tuya_switch(
        dp_id=7,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )

    # DP14 = window_detection (enable/disable open window detection)
    .tuya_switch(
        dp_id=14,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Window detection",
    )

    # DP15 = window_open (binary sensor, open/closed)
    .tuya_binary_sensor(
        dp_id=15,
        attribute_name="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        fallback_name="Window open",
    )

    # DP36 = frost_protection
    .tuya_switch(
        dp_id=36,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )

    # DP47 = local_temperature_calibration (-9.5 to 9.5°C, value x10)
    .tuya_number(
        dp_id=47,
        attribute_name="local_temperature_calibration",
        type=t.int32s,
        min_value=-95,
        max_value=95,
        unit=UnitOfTemperature.CELSIUS,
        step=5,
        translation_key="local_temperature_calibration",
        fallback_name="Temperature calibration",
    )

    .skip_configuration()
    .add_to_registry()
)
