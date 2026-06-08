"""SONOFF S60ZBTPG smart socket overload protection quirk."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef, ZCLCommandDef


class SonoffCustomCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11
    enable_config = {0x700C: 0x01, 0x7010: 0x01}

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            manufacturer_code=None,
        )

        fault_code = ZCLAttributeDef(
            id=0x0010,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        outlet_control_protect_setting = ZCLAttributeDef(
            id=0x7007,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        ac_current_max_overload_enable = ZCLAttributeDef(
            id=0x700C,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        ac_current_max_overload = ZCLAttributeDef(
            id=0x700D,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ac_voltage_max_overload_enable = ZCLAttributeDef(
            id=0x700E,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        ac_voltage_max_overload = ZCLAttributeDef(
            id=0x700F,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ac_power_max_overload_enable = ZCLAttributeDef(
            id=0x7010,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        ac_power_max_overload = ZCLAttributeDef(
            id=0x7011,
            type=t.uint32_t,
            manufacturer_code=None,
        )

    async def bind(self):
        """Bind cluster and force-enable non-user exposed protections."""
        result = await super().bind()
        await self.write_attributes(self.enable_config)
        return result

    @staticmethod
    def _has_attribute(
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        attr_def: foundation.ZCLAttributeDef,
    ) -> bool:
        """Return True when an attribute write payload contains attr_def."""
        return (
            attr_def in attributes
            or attr_def.id in attributes
            or attr_def.name in attributes
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Force-enable overload protection before writing protected thresholds."""
        result = []

        enable_writes: dict[int, int] = {}
        if self._has_attribute(attributes, self.AttributeDefs.ac_current_max_overload):
            enable_writes[self.AttributeDefs.ac_current_max_overload_enable.id] = 0x01
        if self._has_attribute(attributes, self.AttributeDefs.ac_power_max_overload):
            enable_writes[self.AttributeDefs.ac_power_max_overload_enable.id] = 0x01

        if enable_writes:
            result += await super().write_attributes(enable_writes, **kwargs)

        result += await super().write_attributes(attributes, **kwargs)
        return result

    class ServerCommandDefs(CustomCluster.ServerCommandDefs):
        """Sonoff manufacturer specific server commands."""

        clear_energy_consumption: Final = ZCLCommandDef(
            id=0x0C,
            schema={
                "deviceType": t.uint8_t,
                "deviceLength": t.uint8_t,
                "EventType": t.uint8_t,
            },
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("SONOFF", "S60ZBTPG")
    .replaces(SonoffCustomCluster)
    .binary_sensor(
        SonoffCustomCluster.AttributeDefs.fault_code.name,
        SonoffCustomCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: x == 0x3020004,
        unique_id_suffix="threshold_protection",
        translation_key="threshold_protection",
        fallback_name="Threshold protection",
    )
    .switch(
        SonoffCustomCluster.AttributeDefs.outlet_control_protect_setting.name,
        SonoffCustomCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="outlet_control_protect_setting",
        fallback_name="Outlet control protect setting",
    )
    .switch(
        SonoffCustomCluster.AttributeDefs.network_led.name,
        SonoffCustomCluster.cluster_id,
        endpoint_id=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .number(
        SonoffCustomCluster.AttributeDefs.ac_current_max_overload.name,
        SonoffCustomCluster.cluster_id,
        cluster_type=ClusterType.Server,
        min_value=0.1,
        max_value=14,
        step=0.1,
        unit=UnitOfElectricCurrent.AMPERE,
        mode="box",
        multiplier=0.001,
        translation_key="ac_current_max_overload",
        fallback_name="AC current max overload",
    )
    .switch(
        SonoffCustomCluster.AttributeDefs.ac_voltage_max_overload_enable.name,
        SonoffCustomCluster.cluster_id,
        endpoint_id=1,
        force_inverted=False,  # Optional: invert on/off
        off_value=0,  # Optional: value written when turning off (default 0)
        on_value=1,  # Optional: value written when turning on (default 1)
        translation_key="ac_voltage_max_overload_enable",
        fallback_name="AC voltage max overload enable",
    )
    .number(
        SonoffCustomCluster.AttributeDefs.ac_voltage_max_overload.name,
        SonoffCustomCluster.cluster_id,
        cluster_type=ClusterType.Server,
        min_value=165,
        max_value=277,
        step=1.0,
        unit=UnitOfElectricPotential.VOLT,
        mode="box",
        multiplier=0.001,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="ac_voltage_max_overload",
        fallback_name="AC voltage max overload",
    )
    .number(
        SonoffCustomCluster.AttributeDefs.ac_power_max_overload.name,
        SonoffCustomCluster.cluster_id,
        cluster_type=ClusterType.Server,
        min_value=0.1,
        max_value=3250.0,
        step=0.1,
        unit=UnitOfPower.WATT,
        mode="box",
        multiplier=0.001,
        device_class=NumberDeviceClass.POWER,
        translation_key="ac_power_max_overload",
        fallback_name="AC power max overload",
    )
    .add_to_registry()
)
