"""Map from manufacturer to standard clusters for thermostatic valves."""

from typing import Any

from zigpy.profiles import zha
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature, UnitOfTime
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaAttributesCluster,
    TuyaMCUCluster,
)


class TuyaThermostatSystemMode(t.enum8):
    """Tuya thermostat system mode enum."""

    Auto = 0x00
    Heat = 0x01
    Off = 0x02


class TuyaThermostatSystemModeV02(t.enum8):
    """Tuya thermostat system mode enum, auto and manual."""

    Auto = 0x00
    Manual = 0x02


class TuyaThermostatEcoMode(t.enum8):
    """Tuya thermostat eco mode enum."""

    Comfort = 0x00
    Eco = 0x01


class State(t.enum8):
    """State option."""

    Off = 0x00
    On = 0x01


class BatteryState(t.enum8):
    """Battery state option."""

    Normal = 0x00
    Low = 0x01


class ScheduleState(t.enum8):
    """Schedule state option."""

    Disabled = 0x00
    Enabled = 0x01


class ScreenOrientation(t.enum8):
    """Screen orientation enum."""

    Up = 0x00
    Right = 0x01
    Down = 0x02
    Left = 0x03


class TuyaDisplayBrightness(t.enum8):
    """Tuya display brightness mode."""

    High = 0x00
    Medium = 0x01
    Low = 0x02


class TuyaMotorThrust(t.enum8):
    """Tuya motor thrust mode."""

    Strong = 0x00
    Middle = 0x01
    Weak = 0x02


class TuyaDisplayOrientation(t.enum8):
    """Tuya display orientation mode."""

    Up = 0x00
    Down = 0x01


class TuyaHysteresis(t.enum8):
    """Tuya hysteresis mode."""

    Comfort = 0x00
    Eco = 0x01


class TuyaPresetMode(t.enum8):
    """Tuya preset mode."""

    Eco = 0x00
    Auto = 0x01
    Off = 0x02
    Heat = 0x03


class TuyaThermostatV2(Thermostat, TuyaAttributesCluster):
    """Tuya local thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id: 3000,
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: Thermostat.ControlSequenceOfOperation.Heating_Only,
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
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.min_heat_setpoint_limit.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.max_heat_setpoint_limit.id
        )


class TuyaThermostatV2NoSchedule(TuyaThermostatV2):
    """Ensures schedule is disabled on system_mode change."""

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: int | None = None,
        **kwargs,
    ) -> list:
        """Catch attribute writes for system_mode and set schedule to off."""
        results = await super().write_attributes(attributes, manufacturer)
        if (
            Thermostat.AttributeDefs.system_mode.id in attributes
            or Thermostat.AttributeDefs.system_mode.name in attributes
        ):
            tuya_cluster = self.endpoint.tuya_manufacturer
            await tuya_cluster.write_attributes({"schedule_enable": False})

        return results


(
    TuyaQuirkBuilder("_TYST11_KGbxAXL2", "GbxAXL2")
    .applies_to("_TYST11_c88teujp", "88teujp")
    .applies_to("_TYST11_azqp6ssj", "zqp6ssj")
    .applies_to("_TYST11_yw7cahqs", "w7cahqs")
    .applies_to("_TYST11_9gvruqf5", "gvruqf5")
    .applies_to("_TYST11_zuhszj9s", "uhszj9s")
    .applies_to("_TYST11_caj4jz0i", "aj4jz0i")
    .applies_to("_TZE200_c88teujp", "TS0601")
    .applies_to("_TZE200_azqp6ssj", "TS0601")
    .applies_to("_TZE200_yw7cahqs", "TS0601")
    .applies_to("_TZE200_9gvruqf5", "TS0601")
    .applies_to("_TZE200_zuhszj9s", "TS0601")
    .applies_to("_TZE200_zr9c0day", "TS0601")
    .applies_to("_TZE200_0dvm9mva", "TS0601")
    .applies_to("_TZE200_h4cgnbzg", "TS0601")
    .applies_to("_TZE200_exfrnlow", "TS0601")
    .applies_to("_TZE200_9m4kmbfu", "TS0601")
    .applies_to("_TZE200_3yp57tby", "TS0601")
    # default device type is `SMART_PLUG` for this,
    # so change it back to keep UID/entity the same
    .replaces_endpoint(1, device_type=zha.DeviceType.THERMOSTAT)
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostatV2NoSchedule.ep_attribute,
        attribute_name=TuyaThermostatV2NoSchedule.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_switch(
        dp_id=8,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_switch(
        dp_id=10,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_number(
        dp_id=27,
        attribute_name=TuyaThermostatV2NoSchedule.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-6,
        max_value=6,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaThermostatV2NoSchedule.ep_attribute,
        attribute_name=TuyaThermostatV2NoSchedule.AttributeDefs.system_mode.name,
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
        dp_id=102,
        ep_attribute=TuyaThermostatV2NoSchedule.ep_attribute,
        attribute_name=TuyaThermostatV2NoSchedule.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_dp(
        dp_id=103,
        ep_attribute=TuyaThermostatV2NoSchedule.ep_attribute,
        attribute_name=TuyaThermostatV2NoSchedule.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .adds(TuyaThermostatV2NoSchedule)
    .tuya_sensor(
        dp_id=104,
        attribute_name="valve_position",
        type=t.int16s,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        translation_key="valve_position",
        fallback_name="Valve position",
    )
    .tuya_binary_sensor(
        dp_id=105,
        attribute_name="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        fallback_name="Battery low",
    )
    .tuya_switch(
        dp_id=106,
        attribute_name="away_mode",
        translation_key="away_mode",
        fallback_name="Away mode",
    )
    .tuya_switch(
        dp_id=108,
        attribute_name="schedule_enable",
        translation_key="schedule_enable",
        fallback_name="Schedule enable",
    )
    .tuya_switch(
        dp_id=130,
        attribute_name="scale_protection",
        translation_key="scale_protection",
        fallback_name="Scale protection",
    )
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE204_rtrmfadk", "TS0601")
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.system_mode.name,
        converter=lambda x: {
            TuyaThermostatSystemMode.Auto: Thermostat.SystemMode.Auto,
            TuyaThermostatSystemMode.Heat: Thermostat.SystemMode.Heat,
            TuyaThermostatSystemMode.Off: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Auto: TuyaThermostatSystemMode.Auto,
            Thermostat.SystemMode.Heat: TuyaThermostatSystemMode.Heat,
            Thermostat.SystemMode.Off: TuyaThermostatSystemMode.Off,
        }[x],
    )
    .tuya_dp(
        dp_id=2,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_dp(
        dp_id=6,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_binary_sensor(
        dp_id=7,
        attribute_name="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        fallback_name="Window open",
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
    .tuya_battery(dp_id=13)
    .tuya_binary_sensor(
        dp_id=14,
        attribute_name="error_or_battery_low",
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="error_or_battery_low",
        fallback_name="Error or battery low",
    )
    .tuya_number(
        dp_id=15,
        attribute_name="min_temperature",
        type=t.uint16_t,
        min_value=1,
        max_value=15,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="min_temperature",
        fallback_name="Min temperature",
    )
    .tuya_number(
        dp_id=16,
        attribute_name="max_temperature",
        type=t.uint16_t,
        min_value=15,
        max_value=35,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="max_temperature",
        fallback_name="Max temperature",
    )
    .tuya_number(
        dp_id=101,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-6,
        max_value=6,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_enum(
        dp_id=114,
        attribute_name="eco_mode",
        enum_class=TuyaThermostatEcoMode,
        translation_key="eco_mode",
        fallback_name="Eco mode",
    )
    .adds(TuyaThermostatV2)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_bvu2wnxz", "TS0601")
    .applies_to("_TZE200_6rdj8dzm", "TS0601")
    .applies_to("_TZE200_9xfjixap", "TS0601")
    .applies_to("_TZE200_p3dbf6qs", "TS0601")
    .applies_to("_TZE200_rxntag7i", "TS0601")
    .applies_to("_TZE200_yqgbrdyo", "TS0601")
    .applies_to("_TZE284_p3dbf6qs", "TS0601")
    .applies_to("_TZE200_rxq4iti9", "TS0601")
    .applies_to("_TZE200_hvaxb2tc", "TS0601")
    .applies_to("_TZE284_o3x45p96", "TS0601")
    .applies_to("_TZE284_c6wv4xyo", "TS0601")
    .applies_to("_TZE204_o3x45p96", "TS0601")
    .applies_to("_TZE204_ogx8u5z6", "TS0601")
    .applies_to("_TZE284_ogx8u5z6", "TS0601")
    .tuya_dp(
        dp_id=2,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.system_mode.name,
        converter=lambda x: {
            TuyaThermostatSystemMode.Auto: Thermostat.SystemMode.Auto,
            TuyaThermostatSystemMode.Heat: Thermostat.SystemMode.Heat,
            TuyaThermostatSystemMode.Off: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Auto: TuyaThermostatSystemMode.Auto,
            Thermostat.SystemMode.Heat: TuyaThermostatSystemMode.Heat,
            Thermostat.SystemMode.Off: TuyaThermostatSystemMode.Off,
        }[x],
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if not x else RunningState.Idle,
    )
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=5,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_number(
        dp_id=47,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-6,
        max_value=6,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_switch(
        dp_id=7,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_binary_sensor(
        dp_id=35,
        attribute_name="error_or_battery_low",
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="error_or_battery_low",
        fallback_name="Error or battery low",
    )
    .tuya_switch(
        dp_id=36,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=39,
        attribute_name="scale_protection",
        translation_key="scale_protection",
        fallback_name="Scale protection",
    )
    .adds(TuyaThermostatV2)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE284_ymldrmzx", "TS0601")  # Tuya TRV603-WZ
    .tuya_dp(
        dp_id=2,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.system_mode.name,
        converter=lambda x: {
            TuyaThermostatSystemModeV02.Auto: Thermostat.SystemMode.Auto,
            TuyaThermostatSystemModeV02.Manual: Thermostat.SystemMode.Heat,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Auto: TuyaThermostatSystemModeV02.Auto,
            Thermostat.SystemMode.Heat: TuyaThermostatSystemModeV02.Manual,
        }[x],
    )
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=5,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_battery(dp_id=6)
    .tuya_switch(
        dp_id=7,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_switch(
        dp_id=14,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_binary_sensor(
        dp_id=15,
        attribute_name="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        fallback_name="Window open",
    )
    .tuya_number(
        dp_id=21,
        attribute_name="holiday_temperature",
        type=t.uint16_t,
        min_value=5,
        max_value=30,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    .tuya_switch(
        dp_id=36,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=39,
        attribute_name="scale_protection",
        translation_key="scale_protection",
        fallback_name="Scale protection",
    )
    .tuya_number(
        dp_id=47,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-6,
        max_value=6,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="boost_heating",
        translation_key="boost_heating",
        fallback_name="Boost heating",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="boost_time",
        type=t.uint16_t,
        min_value=0,
        max_value=1000,
        unit=UnitOfTime.MINUTES,
        step=1,
        translation_key="boost_time",
        fallback_name="Boost time",
    )
    # 103-109 are schedule DPs, skipped
    .tuya_switch(
        dp_id=110,
        attribute_name="holiday_mode",
        translation_key="holiday_mode",
        fallback_name="Holiday mode",
    )
    .tuya_enum(
        dp_id=111,
        attribute_name="screen_orientation",
        enum_class=ScreenOrientation,
        translation_key="screen_orientation",
        fallback_name="Screen orientation",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="antifrost_temperature",
        type=t.uint16_t,
        min_value=5,
        max_value=30,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="antifrost_temperature",
        fallback_name="Antifrost temperature",
    )
    .tuya_switch(
        dp_id=113,
        attribute_name="heating_stop",
        translation_key="heating_stop",
        fallback_name="Heating stop",
    )
    # DP 115 programming_mode, z2m doesn't expose
    .tuya_number(
        dp_id=116,
        attribute_name="eco_temperature",
        type=t.uint16_t,
        min_value=5,
        max_value=30,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="eco_temperature",
        fallback_name="Eco temperature",
    )
    .tuya_number(
        dp_id=117,
        attribute_name="comfort_temperature",
        type=t.uint16_t,
        min_value=5,
        max_value=30,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="comfort_temperature",
        fallback_name="Comfort temperature",
    )
    .tuya_sensor(
        dp_id=118,
        attribute_name="fault_code",
        type=t.int16s,
        translation_key="fault_code",
        fallback_name="Fault code",
    )
    .adds(TuyaThermostatV2)
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)


# Moes TRV602Z and TRV801Z
(
    TuyaQuirkBuilder("_TZE204_qyr2m29i", "TS0601")
    .applies_to("_TZE204_ltwbm23f", "TS0601")
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=5,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_number(
        dp_id=47,
        attribute_name=TuyaThermostatV2NoSchedule.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-6,
        max_value=6,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_dp_multi(
        dp_id=2,
        attribute_mapping=[
            DPToAttributeMapping(
                ep_attribute=TuyaThermostatV2.ep_attribute,
                attribute_name=TuyaThermostatV2.AttributeDefs.system_mode.name,
                converter=lambda x: {
                    TuyaPresetMode.Auto: Thermostat.SystemMode.Auto,
                    TuyaPresetMode.Eco: Thermostat.SystemMode.Auto,
                    TuyaPresetMode.Heat: Thermostat.SystemMode.Heat,
                    TuyaPresetMode.Off: Thermostat.SystemMode.Off,
                }[x],
                dp_converter=lambda x: {
                    Thermostat.SystemMode.Auto: TuyaPresetMode.Auto,
                    Thermostat.SystemMode.Heat: TuyaPresetMode.Heat,
                    Thermostat.SystemMode.Off: TuyaPresetMode.Off,
                }[x],
            ),
            DPToAttributeMapping(
                ep_attribute=TuyaMCUCluster.ep_attribute,
                attribute_name="preset_mode",
            ),
        ],
    )
    .tuya_attribute(
        dp_id=2,
        attribute_name="preset_mode",
        type=t.uint16_t,
        is_manufacturer_specific=True,
    )
    .enum(
        attribute_name="preset_mode",
        cluster_id=TUYA_CLUSTER_ID,
        enum_class=TuyaPresetMode,
        translation_key="preset_mode",
        fallback_name="Preset mode",
    )
    .tuya_battery(dp_id=6)
    .tuya_switch(
        dp_id=7,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_number(
        dp_id=9,
        attribute_name="max_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=15,
        max_value=35,
        step=1,
        multiplier=0.1,
        translation_key="max_temperature",
        fallback_name="Max temperature",
    )
    .tuya_number(
        dp_id=10,
        attribute_name="min_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=1,
        max_value=15,
        step=1,
        multiplier=0.1,
        translation_key="min_temperature",
        fallback_name="Min temperature",
    )
    .tuya_switch(
        dp_id=14,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_binary_sensor(
        dp_id=15,
        attribute_name="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        fallback_name="Window open",
    )
    .tuya_enum(
        dp_id=110,
        attribute_name="motor_thrust",
        enum_class=TuyaMotorThrust,
        translation_key="motor_thrust",
        fallback_name="Motor thrust",
    )
    .tuya_enum(
        dp_id=111,
        attribute_name="display_brightness",
        enum_class=TuyaDisplayBrightness,
        translation_key="display_brightness",
        fallback_name="Display brightness",
    )
    .tuya_enum(
        dp_id=113,
        attribute_name="display_orientation",
        enum_class=TuyaDisplayOrientation,
        translation_key="display_orientation",
        fallback_name="Display orientation",
    )
    .tuya_sensor(
        dp_id=114,
        attribute_name="valve_position",
        type=t.int16s,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        translation_key="valve_position",
        fallback_name="Valve position",
    )
    .tuya_number(
        dp_id=119,
        attribute_name="comfort_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=30,
        step=1,
        multiplier=0.1,
        translation_key="comfort_temperature",
        fallback_name="Comfort temperature",
    )
    .tuya_number(
        dp_id=120,
        attribute_name="eco_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=30,
        step=1,
        multiplier=0.1,
        translation_key="eco_temperature",
        fallback_name="Eco temperature",
    )
    .tuya_number(
        dp_id=121,
        attribute_name="holiday_temperature",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5,
        max_value=30,
        step=1,
        multiplier=0.1,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    .tuya_enum(
        dp_id=127,
        attribute_name="hysteresis_mode",
        enum_class=TuyaHysteresis,
        translation_key="hysteresis_mode",
        fallback_name="Hysteresis mode",
    )
    .adds(TuyaThermostatV2)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_ne4pikwm", "TS0601")  # Nedis ZBHTR20WT
    .applies_to("_TZE284_ne4pikwm", "TS0601")
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.running_state.name,
        converter=lambda x: RunningState.Heat_State_On if x else RunningState.Idle,
    )
    .tuya_switch(
        dp_id=8,
        attribute_name="window_detection",
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .tuya_switch(
        dp_id=10,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_number(
        dp_id=27,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        type=t.int32s,
        min_value=-6,
        max_value=6,
        unit=UnitOfTemperature.CELSIUS,
        step=1,
        translation_key="local_temperature_calibration",
        fallback_name="Local temperature calibration",
    )
    .tuya_switch(
        dp_id=40,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.system_mode.name,
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
        dp_id=102,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_dp(
        dp_id=103,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_binary_sensor(
        dp_id=105,
        attribute_name="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        fallback_name="Battery low",
    )
    .tuya_switch(
        dp_id=106,
        attribute_name="away_mode",
        translation_key="away_mode",
        fallback_name="Away mode",
    )
    .tuya_switch(
        dp_id=108,
        attribute_name="schedule_mode",
        translation_key="schedule_mode",
        fallback_name="Schedule mode",
    )
    .tuya_switch(
        dp_id=130,
        attribute_name="scale_protection",
        translation_key="scale_protection",
        fallback_name="Scale protection",
    )
    .adds(TuyaThermostatV2)
    .skip_configuration()
    .add_to_registry()
)
