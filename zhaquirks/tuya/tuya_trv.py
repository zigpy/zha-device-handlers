"""Map from manufacturer to standard clusters for thermostatic valves."""

from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster


class TuyaThermostatSystemMode(t.enum8):
    """Tuya thermostat system mode enum."""

    Auto = 0x00
    Heat = 0x01
    Off = 0x02


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


class TuyaThermostatV2(Thermostat, TuyaAttributesCluster):
    """Tuya local thermostat cluster."""

    manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID
    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.min_heat_setpoint_limit.id: 500,
        Thermostat.AttributeDefs.max_heat_setpoint_limit.id: 3000,
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

    async def write_attributes(self, attributes, manufacturer=None):
        """Overwrite to force manufacturer code."""
        return await super().write_attributes(
            attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
        )


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
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.running_state.name,
        converter=lambda x: 0x01 if not x else 0x00,  # Heat, Idle
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
    .tuya_dp(
        dp_id=27,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        converter=lambda x: x,
        dp_converter=lambda x: 0xFFFFFFFF - x if x > 6 else x,
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
        converter=lambda x: Thermostat.SystemMode.Heat
        if x == TuyaThermostatSystemMode.Heat
        else Thermostat.SystemMode.Off,
        dp_converter=lambda x: TuyaThermostatSystemMode.Heat
        if x == Thermostat.SystemMode.Heat
        else 0x00,
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
    .adds(TuyaThermostatV2)
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
        converter=lambda x: 0x01 if not x else 0x00,  # Heat, Idle
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
    .tuya_dp(
        dp_id=101,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        converter=lambda x: x,
        dp_converter=lambda x: x + 0x100000000 if x < 0 else x,
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
        converter=lambda x: 0x01 if not x else 0x00,  # Heat, Idle
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
    .tuya_dp(
        dp_id=47,
        ep_attribute=TuyaThermostatV2.ep_attribute,
        attribute_name=TuyaThermostatV2.AttributeDefs.local_temperature_calibration.name,
        converter=lambda x: x,
        dp_converter=lambda x: x + 0x100000000 if x < 0 else x,
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
