"""Module for Legrand Cable Outlet (with pilot wire functionality)."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, add_to_registry_v2
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.hvac import SystemMode, Thermostat
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks import Bus
from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID

MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC40  # 64576

ZCL_SYSTEM_MODE = Thermostat.attributes_by_name["system_mode"].id

HEAT_MODE_ATTR = 0x00
OPERATION_PRESET_ATTR = 0x4002


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


class HeatMode(t.enum8):
    """Heat mode."""

    Comfort = 0x00
    Comfort_minus_1 = 0x01
    Comfort_minus_2 = 0x02
    Eco = 0x03
    Frost_protection = 0x04
    Off = 0x05


class LegrandCableOutletThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster for Legrand Cable Outlet."""

    _CONSTANT_ATTRIBUTES = {
        0x001B: Thermostat.ControlSequenceOfOperation.Heating_Only,
    }

    attributes = Thermostat.attributes.copy()
    attributes.update(
        {
            OPERATION_PRESET_ATTR: ("operation_preset", HeatMode),
        }
    )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)

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
        self._update_attribute(ZCL_SYSTEM_MODE, system_mode)
        self._update_attribute(OPERATION_PRESET_ATTR, value)

    async def write_attributes(self, attributes, manufacturer=None):
        """Implement writeable attributes."""

        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == OPERATION_PRESET_ATTR:
                attrs[HEAT_MODE_ATTR] = value
            elif attr_id == ZCL_SYSTEM_MODE:
                current = self._attr_cache.get(ZCL_SYSTEM_MODE)
                if current != value:
                    attrs[HEAT_MODE_ATTR] = (
                        HeatMode.Comfort if value == SystemMode.Heat else HeatMode.Off
                    )
            else:
                attrs[attr] = value
        await self.endpoint.cable_outlet_cluster.write_attributes(attrs, manufacturer)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


class LegrandCableOutletCluster(CustomCluster):
    """Legrand second manufacturer-specific cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID_2
    name = "CableOutlet"
    ep_attribute = "cable_outlet_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for LegrandCluster."""

        heat_mode = ZCLAttributeDef(
            id=HEAT_MODE_ATTR,
            type=HeatMode,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        set_heat_mode = ZCLCommandDef(
            id=HEAT_MODE_ATTR,
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
            if attr_id == HEAT_MODE_ATTR:
                await self.set_heat_mode(value, manufacturer=manufacturer)
            else:
                attrs[attr] = value
        return await super().write_attributes(attrs, manufacturer)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == HEAT_MODE_ATTR:
            self.endpoint.device.thermostat_bus.listener_event(
                "heat_mode_change", value
            )


class LegrandCableOutletThermostat(CustomDeviceV2):
    """Legrand Cable Outlet Thermostat device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_bus = Bus()
        super().__init__(*args, **kwargs)


(
    add_to_registry_v2(f" {LEGRAND}", " Cable outlet")
    .device_class(LegrandCableOutletThermostat)
    .replaces(LegrandCluster)
    .replaces(LegrandCableOutletCluster)
    .replaces(LegrandCluster, cluster_type=ClusterType.Client)
    .adds(LegrandCableOutletThermostatCluster)
)
