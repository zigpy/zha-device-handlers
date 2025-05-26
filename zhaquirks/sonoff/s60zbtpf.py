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
    manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        outlet_control_protect_setting = ZCLAttributeDef(
            id=0x7007,
            type=t.uint8_t,
        )
        ac_current_max_overload_enable = ZCLAttributeDef(
            id=0x700C,
            type=t.uint8_t,
        )
        ac_voltage_max_overload_enable = ZCLAttributeDef(
            id=0x700E,
            type=t.uint8_t,
        )
        ac_power_max_overload_enable = ZCLAttributeDef(
            id=0x7010,
            type=t.uint8_t,
        )
        ac_current_max_overload = ZCLAttributeDef(
            id=0x700D,
            type=t.uint32_t,
        )
        ac_voltage_max_overload = ZCLAttributeDef(
            id=0x700F,
            type=t.uint32_t,
        )
        ac_power_max_overload = ZCLAttributeDef(
            id=0x7011,
            type=t.uint32_t,
        )


    class ServerCommandDefs(zcl_f.BaseCommandDefs):
        """Server command definitions."""

        self_test: Final = zcl_f.ZCLCommandDef(
            id=0x00, schema={"identify_time": t.uint8_t}, direction=False
        )
 
(
    QuirkBuilder("SONOFF", "S60ZBTPF")
    .replaces(SonoffCluster)
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
        SonoffCluster.AttributeDefs.ac_current_max_overload.name,
        SonoffCluster.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        min_value=0.1,
        max_value=17.0,
        step=0.1,
        unit = UnitOfElectricCurrent.AMPERE,
        multiplier = 0.001,
        translation_key = "ac_current_max_overload",
        device_class = NumberDeviceClass.CURRENT,
        fallback_name = "AC current max overload",
    )
    .number(
        SonoffCluster.AttributeDefs.ac_voltage_max_overload.name,
        SonoffCluster.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        min_value=165.0,
        max_value=277.0,
        step=1.0,
        unit = UnitOfElectricPotential.VOLT,
        multiplier = 0.001,
        translation_key = "ac_voltage_max_overload",
        device_class = NumberDeviceClass.POWER,
        fallback_name = "AC voltage max overload",
    )
    .number(
        SonoffCluster.AttributeDefs.ac_power_max_overload.name,
        SonoffCluster.cluster_id,
        cluster_type=ClusterType.Server,
        endpoint_id=1,
        min_value=0.1,
        max_value=4000.0,
        step=0.1,
        unit = UnitOfPower.WATT,
        multiplier = 0.001,
        translation_key = "ac_power_max_overload",
        device_class = NumberDeviceClass.POWER,
        fallback_name = "AC power max overload",
    )
    .add_to_registry()
)
