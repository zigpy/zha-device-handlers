"""Module for Legrand Cable Outlet (with pilot wire functionality)."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import add_to_registry_v2
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID

MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC40  # 64576

HEAT_MODE_ATTR = 0x00
ZCL_DEVICE_MODE = 0x4000


class DeviceMode(t.enum16):
    """Device mode."""

    Standard = 0x01
    Wire_pilot = 0x02


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
        device_mode_enum = ZCLAttributeDef(
            id=ZCL_DEVICE_MODE,
            type=DeviceMode,
        )

    async def write_attributes(self, attributes, manufacturer=None) -> list:
        """Write attributes to the cluster."""

        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            if attr_id == ZCL_DEVICE_MODE:
                attrs[0x0000] = [value, 0x00]
            else:
                attrs[attr] = value
        return await super().write_attributes(attrs, manufacturer)

    def _update_attribute(self, attrid, value) -> None:
        super()._update_attribute(attrid, value)
        if attrid == 0x0000:
            self._update_attribute(ZCL_DEVICE_MODE, value[0])


class HeatMode(t.enum8):
    """Heat mode."""

    Comfort = 0x00
    Comfort_minus_1 = 0x01
    Comfort_minus_2 = 0x02
    Eco = 0x03
    Frost_protection = 0x04
    Off = 0x05


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


(
    add_to_registry_v2(f" {LEGRAND}", " Cable outlet")
    .replaces(LegrandCluster)
    .replaces(LegrandCableOutletCluster)
    .replaces(LegrandCluster, cluster_type=ClusterType.Client)
    .enum(
        attribute_name=LegrandCluster.AttributeDefs.device_mode_enum.name,
        cluster_id=LegrandCluster.cluster_id,
        enum_class=DeviceMode,
        translation_key="device_mode",
    )
)
