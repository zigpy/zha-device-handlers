"""Sonoff TRVZB - Zigbee Thermostatic Radiator Valve."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTemperature
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

    @property
    def _is_manuf_specific(self):
        return False


(
    QuirkBuilder("SONOFF", "TRVZB")
    .replaces(CustomSonoffCluster)
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
    .add_to_registry()
)
