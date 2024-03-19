"""Module for Legrand Cable Outlet with pilot wire functionality."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import add_to_registry_v2
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import SystemMode, Thermostat
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks import LocalDataCluster
from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID

MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC40  # 64576


WIRE_PILOT_MODE_ATTR = 0x4000

LEGRAND_HEAT_MODE_ATTR = 0x00
THERMOSTAT_HEAT_MODE_ATTR = 0x4000
THERMOSTAT_SYSTEM_MODE_ATTR = Thermostat.attributes_by_name["system_mode"].id


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        device_mode = ZCLAttributeDef(
            id=0x0000,
            type=t.data16,
            is_manufacturer_specific=True,
        )
        led_dark = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        led_on = ZCLAttributeDef(
            id=0x0002,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        wire_pilot_mode = ZCLAttributeDef(id=WIRE_PILOT_MODE_ATTR, type=t.Bool)

    async def write_attributes(self, attributes, manufacturer=None) -> list:
        """Write attributes to the cluster."""

        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == WIRE_PILOT_MODE_ATTR:
                attrs[0x0000] = [0x02, 0x00] if value else [0x01, 0x00]
            else:
                attrs[attr] = value
        return await super().write_attributes(attrs, manufacturer)

    def _update_attribute(self, attrid, value) -> None:
        super()._update_attribute(attrid, value)
        if attrid == 0x0000:
            self._update_attribute(WIRE_PILOT_MODE_ATTR, value[0] == 0x02)


class HeatMode(t.enum8):
    """Heat mode."""

    Comfort = 0x00
    Comfort_minus_1 = 0x01
    Comfort_minus_2 = 0x02
    Eco = 0x03
    Frost_protection = 0x04
    Off = 0x05


class LegrandWirePilotCluster(CustomCluster):
    """Legrand wire pilot manufacturer-specific cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID_2
    name = "LegrandWirePilotCluster"
    ep_attribute = "legrand_wire_pilot_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for LegrandCluster."""

        heat_mode = ZCLAttributeDef(
            id=LEGRAND_HEAT_MODE_ATTR,
            type=HeatMode,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        set_heat_mode = ZCLCommandDef(
            id=LEGRAND_HEAT_MODE_ATTR,
            schema={"mode": HeatMode},
            direction=Direction.Client_to_Server,
            is_manufacturer_specific=True,
        )

    async def write_attributes(self, attributes, manufacturer=None) -> list:
        """Write attributes to the cluster."""

        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == LEGRAND_HEAT_MODE_ATTR:
                await self.set_heat_mode(value, manufacturer=manufacturer)
        return await super().write_attributes(attrs, manufacturer)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == LEGRAND_HEAT_MODE_ATTR:
            self.endpoint.thermostat.heat_mode_change(value)


class LegrandWirePilotThermostatCluster(LocalDataCluster, Thermostat):
    """Thermostat cluster for Legrand wire pilot thermostats."""

    _CONSTANT_ATTRIBUTES = {0x001B: Thermostat.ControlSequenceOfOperation.Heating_Only}

    class AttributeDefs(Thermostat.AttributeDefs):
        """Attribute definitions."""

        heat_mode = ZCLAttributeDef(
            id=THERMOSTAT_HEAT_MODE_ATTR,
            type=HeatMode,
        )

    async def write_attributes(self, attributes, manufacturer=None) -> list:
        """Write attributes to the cluster."""

        attrs = {}
        mode: HeatMode = None
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == THERMOSTAT_HEAT_MODE_ATTR:
                mode = value
            elif attr_id == THERMOSTAT_SYSTEM_MODE_ATTR:
                current = self._attr_cache.get(THERMOSTAT_SYSTEM_MODE_ATTR)
                if current != value:
                    mode = (
                        HeatMode.Comfort if value == SystemMode.Heat else HeatMode.Off
                    )
            else:
                attrs[attr] = value

        if mode is not None:
            await self.endpoint.legrand_wire_pilot_cluster.set_heat_mode(
                mode, manufacturer=manufacturer
            )
        return await super().write_attributes(attrs, manufacturer)

    def heat_mode_change(self, value):
        """Handle the change in heat mode."""

        system_mode = SystemMode.Off
        if value in (
            HeatMode.Comfort,
            HeatMode.Comfort_minus_1,
            HeatMode.Comfort_minus_2,
            HeatMode.Eco,
            HeatMode.Frost_protection,
        ):
            system_mode = SystemMode.Heat

        """Heat mode changed reported."""
        self._update_attribute(THERMOSTAT_SYSTEM_MODE_ATTR, system_mode)
        self._update_attribute(THERMOSTAT_HEAT_MODE_ATTR, value)


(
    add_to_registry_v2(f" {LEGRAND}", " Cable outlet")
    .replaces(LegrandCluster)
    .replaces(LegrandWirePilotCluster)
    .replaces(LegrandCluster, cluster_type=ClusterType.Client)
    .adds(LegrandWirePilotThermostatCluster)
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.wire_pilot_mode.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="wire_pilot_mode",
    )
)
