"""Sonoff S60ZBTPF - Zigbee Smart Plug."""

from typing import Final
from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zha.application.platforms.number.const import NumberMode
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl import ClusterType
from zigpy.quirks import CustomDevice
import zigpy.zcl.foundation as zcl_f


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # network_led = ZCLAttributeDef(
        #     name="network_led",
        #     id=0x0001,
        #     type=t.Bool,
        # )
        outlet_control_protect_setting = ZCLAttributeDef(
            name="outlet_control_protect_setting",
            id=0x7007,
            type=t.uint8_t,
        )
        ac_current_max_overload_enable = ZCLAttributeDef(
            name="ac_current_max_overload_enable",
            id=0x700C,
            type=t.uint8_t,
        )
        ac_voltage_max_overload_enable = ZCLAttributeDef(
            name="ac_voltage_max_overload_enable",
            id=0x700E,
            type=t.uint8_t,
        )
        ac_power_max_overload_enable = ZCLAttributeDef(
            name="ac_power_max_overload_enable",
            id=0x7010,
            type=t.uint8_t,
        )
        ac_current_max_overload = ZCLAttributeDef(
            name="ac_current_max_overload",
            id=0x700D,
            type=t.uint32_t,
        )
        ac_voltage_max_overload = ZCLAttributeDef(
            name="ac_voltage_max_overload",
            id=0x700F,
            type=t.uint32_t,
        )
        ac_power_max_overload = ZCLAttributeDef(
            name="ac_power_max_overload",
            id=0x7011,
            type=t.uint32_t,
        )


    class ServerCommandDefs(zcl_f.BaseCommandDefs):
        """Server command definitions."""

        self_test: Final = zcl_f.ZCLCommandDef(
            id=0x00, schema={"identify_time": t.uint8_t}, direction=False
        )

    async def _read_attributes(
        self,
        attribute_ids: list[t.uint16_t],
        *args,
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ):
        """Read attributes ZCL foundation command."""
        return await super()._read_attributes(
            attribute_ids,
            *args,
            manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID,
            **kwargs,
        )

    @property
    def _is_manuf_specific(self):
        return False


class SonoffNetworkLedSetType(types.enum8):
    """network led set type."""
    Off = 0x00
    On = 0x01

(
    QuirkBuilder("SONOFF", "S60ZBTPF")
    .replaces(SonoffCluster)
    # .enum(
    #     SonoffCluster.AttributeDefs.network_led.name,
    #     SonoffNetworkLedSetType,
    #     0xFC11,
    #     translation_key = "network_led",
    #     fallback_name = "Network led",
    # )
    .switch(
        SonoffCluster.AttributeDefs.outlet_control_protect_setting.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="outlet_control_protect_setting",
        fallback_name="Outlet control protect setting",
    )
    .switch(
        SonoffCluster.AttributeDefs.ac_current_max_overload_enable.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="ac_current_max_overload_enable",
        fallback_name="AC current max overload enable",
    )
    .switch(
        SonoffCluster.AttributeDefs.ac_voltage_max_overload_enable.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="ac_voltage_max_overload_enable",
        fallback_name="AC voltage max overload enable",
    )
    .switch(
        SonoffCluster.AttributeDefs.ac_power_max_overload_enable.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="ac_power_max_overload_enable",
        fallback_name="AC power max overload enable",
    )
    .number(
        "ac_current_max_overload",
        0xFC11,
        ClusterType.Server,
        1,
        0.1,
        17.0,
        0.1,
        unit = UnitOfElectricCurrent.AMPERE,
        multiplier = 0.001,
        translation_key = "ac_current_max_overload",
        device_class = NumberDeviceClass.CURRENT,
        fallback_name = "AC current max overload",
    )
    .number(
        "ac_voltage_max_overload",
        0xFC11,
        ClusterType.Server,
        1,
        165.0,
        277.0,
        1.0,
        unit = UnitOfElectricPotential.VOLT,
        multiplier = 0.001,
        translation_key = "ac_voltage_max_overload",
        device_class = NumberDeviceClass.POWER,
        fallback_name = "AC voltage max overload",
    )
    .number(
        "ac_power_max_overload",
        0xFC11,
        ClusterType.Server,
        1,
        0.1,
        4000.0,
        0.1,
        unit = UnitOfPower.WATT,
        multiplier = 0.001,
        translation_key = "ac_power_max_overload",
        device_class = NumberDeviceClass.POWER,
        fallback_name = "AC power max overload",
    )
    .add_to_registry()
)

# class SonoffS60zb(CustomDevice):
