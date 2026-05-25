"""SONOFF S60ZBTPF - Smart Socket with power measurement fix."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.quirks.v2 import EntityType, QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from zigpy.zcl import foundation
from zigpy.zcl import ClusterType
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

        faultCode = ZCLAttributeDef(
            id=0x0010,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ACCurrentMaxOverloadEnable = ZCLAttributeDef(
            id=0x700C,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        ACCurrentMaxOverload = ZCLAttributeDef(
            id=0x700D,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ACVoltageMaxOverloadEnable = ZCLAttributeDef(
            id=0x700E,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        ACVoltageMaxOverload = ZCLAttributeDef(
            id=0x700F,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ACPowerMaxOverloadEnable = ZCLAttributeDef(
            id=0x7010,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        ACPowerMaxOverload = ZCLAttributeDef(
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
        return attr_def in attributes or attr_def.id in attributes or attr_def.name in attributes

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Force-enable overload protection before writing protected thresholds."""
        result = []

        enable_writes: dict[int, int] = {}
        if self._has_attribute(attributes, self.AttributeDefs.ACCurrentMaxOverload):
            enable_writes[self.AttributeDefs.ACCurrentMaxOverloadEnable.id] = 0x01
        if self._has_attribute(attributes, self.AttributeDefs.ACPowerMaxOverload):
            enable_writes[self.AttributeDefs.ACPowerMaxOverloadEnable.id] = 0x01

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
    QuirkBuilder("SONOFF", "BASIC-ZB1GSP")
    .replaces(SonoffCustomCluster)

    .command_button(
        SonoffCustomCluster.ServerCommandDefs.clear_energy_consumption.name,
        SonoffCustomCluster.cluster_id,
        command_kwargs={
            "deviceType": 0x02,
            "deviceLength": 0x01,
            "EventType": 0x00,
        },
        translation_key="clear_energy_consumption",
        fallback_name="Clear energy consumption",
    )

    .binary_sensor(
        SonoffCustomCluster.AttributeDefs.faultCode.name,
        SonoffCustomCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: x == 0x6020004,
        unique_id_suffix="threshold_protection",
        translation_key="threshold_protection", 
        fallback_name="Threshold protection",
    )
    .switch(
        SonoffCustomCluster.AttributeDefs.network_led.name,
        SonoffCustomCluster.cluster_id,
        endpoint_id=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .number(
        SonoffCustomCluster.AttributeDefs.ACCurrentMaxOverload.name,
        SonoffCustomCluster.cluster_id,
        cluster_type=ClusterType.Server,
        min_value=0.1,
        max_value=32,
        step=0.1,
        unit=UnitOfElectricCurrent.AMPERE,
        mode="box",
        multiplier=0.001,
        translation_key="AC_Current_Max_Overload",
        fallback_name="AC current max overload",
    )
    .switch(
        SonoffCustomCluster.AttributeDefs.ACVoltageMaxOverloadEnable.name,
        SonoffCustomCluster.cluster_id, 
        endpoint_id=1,
        force_inverted=False,             # Optional: invert on/off
        off_value=0,                      # Optional: value written when turning off (default 0)
        on_value=1,                       # Optional: value written when turning on (default 1)
        translation_key="AC_Voltage_Max_Overload_Enable",
        fallback_name="AC voltage max overload enable",
    )
    .number(
        SonoffCustomCluster.AttributeDefs.ACVoltageMaxOverload.name,
        SonoffCustomCluster.cluster_id,
        cluster_type=ClusterType.Server,
        min_value=85,
        max_value=277,
        step=1.0,
        unit=UnitOfElectricPotential.VOLT,
        mode="box",
        multiplier=0.001,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="AC_Voltage_Max_Overload",
        fallback_name="AC voltage max overload",
    )
    .number(
        SonoffCustomCluster.AttributeDefs.ACPowerMaxOverload.name,
        SonoffCustomCluster.cluster_id,
        cluster_type=ClusterType.Server,
        min_value=10,
        max_value=7680,
        step=1.0,
        unit=UnitOfPower.WATT,
        mode="box",
        multiplier=0.001, 
        device_class=NumberDeviceClass.POWER,
        translation_key="AC_Power_Max_Overload",
        fallback_name="AC power max overload",
    )
    .add_to_registry()
)
