"""Sonoff S60ZBTPG - Zigbee Smart Plug."""

from typing import (
    Final,
    Any,
)
from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
import zigpy.zcl.foundation as zcl_f
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zigpy.zcl.clusters.general import (
    OnOff,
)

class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(
            name="network_led",
            id=0x0001,
            type=t.Bool,
        )
        outlet_Control_Protect_Setting = ZCLAttributeDef(
            name="outlet_Control_Protect_Setting",
            id=0x7007,
            type=t.uint8_t,
        )
        ac_Current_Max_Overload_Enable = ZCLAttributeDef(
            name="ac_Current_Max_Overload_Enable",
            id=0x700C,
            type=t.uint8_t,
        )
        ac_Voltage_Max_Overload_Enable = ZCLAttributeDef(
            name="ac_Voltage_Max_Overload_Enable",
            id=0x700E,
            type=t.uint8_t,
        )
        ac_Power_Max_Overload_Enable = ZCLAttributeDef(
            name="ac_Power_Max_Overload_Enable",
            id=0x7010,
            type=t.uint8_t,
        )
        ac_Current_Max_Overload = ZCLAttributeDef(
            name="ac_Current_Max_Overload",
            id=0x700D,
            type=t.uint32_t,
        )
        ac_Voltage_Max_Overload = ZCLAttributeDef(
            name="ac_Voltage_Max_Overload",
            id=0x700F,
            type=t.uint32_t,
        )
        ac_Power_Max_Overload = ZCLAttributeDef(
            name="ac_Power_Max_Overload",
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

class PrivateOnoffCluster(OnOff, CustomCluster):
    """Private Onoff Cluster"""
    
    cluster_id = 0x0006

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.on_off.id:
            if value == False:
                self.endpoint.electrical_measurement.update_attribute(
                    ElectricalMeasurement.AttributeDefs.active_power.id,
                    0,
                )
                self.endpoint.electrical_measurement.update_attribute(
                    ElectricalMeasurement.AttributeDefs.rms_current.id,
                    0,
                )

class PrivateElectricalMeasurementCluster(ElectricalMeasurement, CustomCluster):
    """Private Electrical Measurement Cluster"""

    cluster_id = 0x0B04

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        if False == self.endpoint.on_off._attr_cache[OnOff.AttributeDefs.on_off.id]:
            if attrid == self.AttributeDefs.active_power.id:
                value = 0
            if attrid == self.AttributeDefs.rms_current.id:
                value = 0
        super()._update_attribute(attrid, value)

(
    QuirkBuilder("SONOFF", "S60ZBTPG")
    .replaces(SonoffCluster)
    .replaces(PrivateOnoffCluster)
    .replaces(PrivateElectricalMeasurementCluster)
    .enum(
        SonoffCluster.AttributeDefs.network_led.name,
        SonoffNetworkLedSetType,
        0xFC11,
        translation_key = "network_led",
        fallback_name = "Network led",
    )
    .switch(
        SonoffCluster.AttributeDefs.outlet_Control_Protect_Setting.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="outlet_Control_Protect_Setting",
        fallback_name="Outlet control protect setting",
    )
    .switch(
        SonoffCluster.AttributeDefs.ac_Current_Max_Overload_Enable.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="ac_Current_Max_Overload_Enable",
        fallback_name="AC current max overload enable",
    )
    .switch(
        SonoffCluster.AttributeDefs.ac_Voltage_Max_Overload_Enable.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="ac_Voltage_Max_Overload_Enable",
        fallback_name="AC voltage max overload enable",
    )
    .switch(
        SonoffCluster.AttributeDefs.ac_Power_Max_Overload_Enable.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="ac_Power_Max_Overload_Enable",
        fallback_name="AC power max overload enable",
    )
    .number(
        "ac_Current_Max_Overload",
        0xFC11,
        ClusterType.Server,
        1,
        0.1,
        14.0,
        0.1,
        unit=UnitOfElectricCurrent.AMPERE,
        multiplier=0.001,
        translation_key="ac_Current_Max_Overload",
        device_class=NumberDeviceClass.CURRENT,
        fallback_name="AC current max overload",
    )
    .number(
        "ac_Voltage_Max_Overload",
        0xFC11,
        ClusterType.Server,
        1,
        165.0,
        277.0,
        1.0,
        unit=UnitOfElectricPotential.VOLT,
        multiplier=0.001,
        translation_key="ac_Voltage_Max_Overload",
        device_class=NumberDeviceClass.POWER,
        fallback_name="AC voltage max overload",
    )
    .number(
        "ac_Power_Max_Overload",
        0xFC11,
        ClusterType.Server,
        1,
        0.1,
        3250.0,
        0.1,
        unit=UnitOfPower.WATT,
        multiplier=0.001,
        translation_key="ac_Power_Max_Overload",
        device_class=NumberDeviceClass.POWER,
        fallback_name="AC power max overload",
    )
    .add_to_registry()
)

# class SonoffS60zb(CustomDevice):
