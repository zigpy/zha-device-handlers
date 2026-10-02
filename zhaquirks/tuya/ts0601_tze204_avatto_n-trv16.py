"""Quirk for AVATTO N-TRV16 TRV (_TZE204_vjpaih9f).

Fixed version with proper system_mode <-> preset_mode mapping.
"""

import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.builder import BinarySensorDeviceClass, EntityType, UnitOfTemperature
from zhaquirks.tuya import TUYA_CLUSTER_ID, TuyaPowerConfigurationCluster3AA
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaMCUCluster,
)


class AvattoPresetMode(t.enum8):
    """AVATTO TRV Preset Mode Enum.

    Maps to Tuya dp_id=2 values.
    """

    Manual = 0x00
    Schedule = 0x01
    Eco = 0x02
    Comfort = 0x03
    FrostProtection = 0x04
    Holiday = 0x05
    Off = 0x06


class AvattoThermostat(Thermostat, TuyaAttributesCluster):
    """AVATTO TRV thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        ),
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,  # 5°C
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 3500,  # 35°C
    }

    def __init__(self, *args, **kwargs):
        """Init the thermostat cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id
        )
        self.add_unsupported_attribute(Thermostat.AttributeDefs.pi_heating_demand.id)


(
    TuyaQuirkBuilder("_TZE204_vjpaih9f", "TS0601")
    # DP 2: Preset mode - maps to BOTH system_mode AND preset_mode
    # This is the key fix: tuya_dp_multi allows one DP to update multiple attributes
    .tuya_dp_multi(
        dp_id=2,
        attribute_mapping=[
            # First mapping: Tuya preset → ZCL system_mode (for HA climate entity)
            DPToAttributeMapping(
                ep_attribute=AvattoThermostat.ep_attribute,
                attribute_name=AvattoThermostat.AttributeDefs.system_mode.name,
                # Incoming: Tuya preset value → ZCL SystemMode
                converter=lambda x: {
                    AvattoPresetMode.Manual: Thermostat.SystemMode.Heat,
                    AvattoPresetMode.Schedule: Thermostat.SystemMode.Auto,
                    AvattoPresetMode.Eco: Thermostat.SystemMode.Auto,
                    AvattoPresetMode.Comfort: Thermostat.SystemMode.Heat,
                    AvattoPresetMode.FrostProtection: Thermostat.SystemMode.Heat,
                    AvattoPresetMode.Holiday: Thermostat.SystemMode.Auto,
                    AvattoPresetMode.Off: Thermostat.SystemMode.Off,
                }.get(AvattoPresetMode(x), Thermostat.SystemMode.Heat),
            ),
            # Second mapping: Also store raw preset_mode on TuyaMCUCluster
            # This allows the preset_mode entity to work
            DPToAttributeMapping(
                ep_attribute=TuyaMCUCluster.ep_attribute,
                attribute_name="preset_mode",
            ),
        ],
        # Outgoing: ZCL SystemMode (arg 1) / raw preset_mode (arg 2, unused here)
        # → Tuya preset value. Both attributes share dp_id=2, so the converter
        # must accept one positional value per mapping above (see tuya_trv.py
        # for the reference pattern this mirrors).
        dp_converter=lambda system_mode, _preset_mode: {
            Thermostat.SystemMode.Off: AvattoPresetMode.Off,
            Thermostat.SystemMode.Auto: AvattoPresetMode.Schedule,
            Thermostat.SystemMode.Heat: AvattoPresetMode.Manual,
        }.get(system_mode, AvattoPresetMode.Manual),
    )
    # Register the preset_mode attribute on the Tuya cluster
    .tuya_attribute(
        dp_id=2,
        attribute_name="preset_mode",
        type=t.uint16_t,
        is_manufacturer_specific=True,
    )
    # Expose preset_mode as a selectable enum entity
    .enum(
        attribute_name="preset_mode",
        cluster_id=TUYA_CLUSTER_ID,
        enum_class=AvattoPresetMode,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    # DP 3: Running state (valve open/closed, i.e., heating or idle)
    .tuya_dp(
        dp_id=3,
        ep_attribute=AvattoThermostat.ep_attribute,
        attribute_name=AvattoThermostat.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    # DP 4: Heating setpoint (target temperature)
    .tuya_dp(
        dp_id=4,
        ep_attribute=AvattoThermostat.ep_attribute,
        attribute_name=AvattoThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,  # Tuya sends decidegrees, ZCL uses centidegrees
        dp_converter=lambda x: x // 10,
    )
    # DP 5: Local temperature (current temperature reading)
    .tuya_dp(
        dp_id=5,
        ep_attribute=AvattoThermostat.ep_attribute,
        attribute_name=AvattoThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    # DP 6: Battery percentage
    .tuya_battery(dp_id=6, power_cfg=TuyaPowerConfigurationCluster3AA)
    # DP 7: Child lock
    .tuya_switch(
        dp_id=7,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # DP 14: Window detection enable/disable
    .tuya_switch(
        dp_id=14,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    # DP 15: Window open status (binary sensor)
    .tuya_binary_sensor(
        dp_id=15,
        attribute_name="window_open",
        translation_key="window_open",
        fallback_name="Window open",
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.WINDOW,
    )
    # DP 21: Holiday temperature setpoint
    .tuya_number(
        dp_id=21,
        attribute_name="holiday_temperature",
        type=t.int32s,
        min_value=5,
        max_value=35,
        unit=UnitOfTemperature.CELSIUS,
        step=0.5,
        multiplier=0.1,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    # DP 35: Battery low indicator
    .tuya_binary_sensor(
        dp_id=35,
        attribute_name="battery_low",
        translation_key="battery_low",
        fallback_name="Battery low",
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.BATTERY,
    )
    # DP 36: Frost protection enable/disable
    .tuya_switch(
        dp_id=36,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    # DP 47: Local temperature calibration (offset)
    .tuya_number(
        dp_id=47,
        attribute_name=AvattoThermostat.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-9.5,
        max_value=9.5,
        unit=UnitOfTemperature.CELSIUS,
        step=0.5,
        multiplier=0.1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    # DP 103: Eco mode temperature
    .tuya_number(
        dp_id=103,
        attribute_name="eco_temperature",
        type=t.int32s,
        min_value=5,
        max_value=35,
        unit=UnitOfTemperature.CELSIUS,
        step=0.5,
        multiplier=0.1,
        translation_key="eco_temperature",
        fallback_name="Eco temperature",
    )
    # DP 104: Comfort mode temperature
    .tuya_number(
        dp_id=104,
        attribute_name="comfort_temperature",
        type=t.int32s,
        min_value=5,
        max_value=35,
        unit=UnitOfTemperature.CELSIUS,
        step=0.5,
        multiplier=0.1,
        translation_key="comfort_temperature",
        fallback_name="Comfort temperature",
    )
    # DP 105: Frost protection temperature
    .tuya_number(
        dp_id=105,
        attribute_name="frost_protection_temperature",
        type=t.int32s,
        min_value=5,
        max_value=35,
        unit=UnitOfTemperature.CELSIUS,
        step=0.5,
        multiplier=0.1,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
    )
    # Add our custom thermostat cluster
    .adds(AvattoThermostat)
    .skip_configuration()
    .add_to_registry()
)
