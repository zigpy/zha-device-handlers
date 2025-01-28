"""Map from manufacturer to standard clusters for thermostatic valves."""

from zigpy.quirks.v2.homeassistant import PERCENTAGE
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
