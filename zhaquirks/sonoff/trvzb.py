"""Sonoff TRVZB - Zigbee Thermostatic Radiator Valve."""
from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import NumberDeviceClass, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTemperature, UnitOfTime
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        child_lock = ZCLAttributeDef(
            id=0x0000,
            type=t.Bool,
        )

        open_window = ZCLAttributeDef(
            id=0x6000,
            type=t.Bool,
        )

        frost_protection_temperature = ZCLAttributeDef(
            id=0x6002,
            type=t.int16s,
        )

        idle_steps = ZCLAttributeDef(
            id=0x6003,
            type=t.uint16_t,
            access="r",
        )

        closing_steps = ZCLAttributeDef(
            id=0x6004,
            type=t.uint16_t,
            access="r",
        )

        valve_opening_limit_voltage = ZCLAttributeDef(
            id=0x6005,
            type=t.uint16_t,
            access="r",
        )

        valve_closing_limit_voltage = ZCLAttributeDef(
            id=0x6006,
            type=t.uint16_t,
            access="r",
        )

        valve_motor_running_voltage = ZCLAttributeDef(
            id=0x6007,
            type=t.uint16_t,
            access="r",
        )

        valve_opening_degree = ZCLAttributeDef(
            id=0x600B,
            type=t.uint8_t,
        )

        valve_closing_degree = ZCLAttributeDef(
            id=0x600C,
            type=t.uint8_t,
        )

        external_temperature_sensor_enable = ZCLAttributeDef(
            id=0x600E,
            type=t.uint8_t,
        )

        external_temperature_sensor_value = ZCLAttributeDef(
            id=0x600D,
            type=t.int16s,
        )

        temperature_control_accuracy = ZCLAttributeDef(
            id=0x6011,
            type=t.int16s,
        )

        temporary_mode = ZCLAttributeDef(
            id=0x6014,
            type=t.uint8_t,
        )

        boost_mode = ZCLAttributeDef(
            id=0x6018,
            type=t.Bool,
            is_manufacturer_specific=True,
        )

        timer_mode = ZCLAttributeDef(
            id=0x6019,
            type=t.Bool,
            is_manufacturer_specific=True,
        )

        temporary_mode_duration = ZCLAttributeDef(
            id=0x6015,
            type=t.uint32_t,
        )

        timer_mode_target_temperature = ZCLAttributeDef(
            id=0x6016,
            type=t.int16s,
        )
        smart_temperature_control = ZCLAttributeDef(
            id=0x6017,
            type=t.bitmap8,
        )


    def _update_attribute(self, attrid, value):
        """Update attribute and handle temporary mode conversion."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.temporary_mode.id:
            # Convert value to individual mode states
            self._update_attribute(self.AttributeDefs.boost_mode.id, value == 0x00)
            self._update_attribute(self.AttributeDefs.timer_mode.id, value == 0x01)

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Handle writing individual mode attributes by updating temporary_mode."""
        mode_attr = self.AttributeDefs.temporary_mode.id
        new_attributes = attributes.copy()
        mode_attr_defs = [
            (self.AttributeDefs.boost_mode, 0x00),
            (self.AttributeDefs.timer_mode, 0x01),
        ]
        for attrid in attributes:
            for attr_def, mode_value in mode_attr_defs:
                if attrid in (attr_def.id, attr_def.name):
                    new_attributes.pop(attrid)
                    new_attributes[mode_attr] = mode_value
                    break
        return await super().write_attributes(new_attributes, manufacturer, **kwargs)
    @property
    def _is_manuf_specific(self):
        return False



(
    QuirkBuilder("SONOFF", "TRVZB")
    .replaces(CustomSonoffCluster)
    .switch(
        CustomSonoffCluster.AttributeDefs.smart_temperature_control.name,
        # ControlModeType,
        CustomSonoffCluster.cluster_id,
        on_value=2,
        off_value=0,
        translation_key="adaptive_mode",
        fallback_name="Adaptive mode",
    )
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
        CustomSonoffCluster.AttributeDefs.timer_mode_target_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=4.0,
        max_value=35.0,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="timer_mode_target_temperature",
        fallback_name="Timer mode target temperature",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temporary_mode_duration.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=1440,
        step=1,
        unit=UnitOfTime.MINUTES,
        multiplier=1 / 60,
        translation_key="temporary_mode_duration",
        fallback_name="Temporary mode duration",
    )
    .write_attr_button(
        attribute_name=CustomSonoffCluster.AttributeDefs.boost_mode.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        attribute_value=0x00,
        translation_key="boost_mode",
        fallback_name="Boost mode",
    )
    .write_attr_button(
        attribute_name=CustomSonoffCluster.AttributeDefs.timer_mode.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        attribute_value=0x01,
        translation_key="timer_mode",
        fallback_name="Timer mode",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.frost_protection_temperature.name,
        CustomSonoffCluster.cluster_id,
        min_value=4.0,
        max_value=35.0,
        step=0.5,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="frost_protection_temperature",
        fallback_name="Frost protection temperature",
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
        device_class=NumberDeviceClass.TEMPERATURE,
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
    .add_to_registry()
)