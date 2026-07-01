"""Module for Legrand Cable Outlet with pilot wire functionality."""

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID


class DeviceMode(t.enum16):
    """Device mode."""

    Switch = 0x0001
    PilotWire = 0x0002


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for LegrandCluster."""

        device_mode = ZCLAttributeDef(
            id=0x0000,
            type=DeviceMode,
            zcl_type=DataTypeId.data16,
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


class PilotWireMode(t.enum8):
    """Pilot Wire mode."""

    Comfort = 0x00
    ComfortMinus1 = 0x01
    ComfortMinus2 = 0x02
    Eco = 0x03
    FrostProtection = 0x04
    Off = 0x05


class LegrandCableOutletCluster(CustomCluster):
    """Legrand Cable Outlet manufacturer-specific cluster."""

    cluster_id = 0xFC40
    name = "Legrand Cable Outlet"
    ep_attribute = "legrand_cable_outlet_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for LegrandCableOutletCluster."""

        pilot_wire_mode = ZCLAttributeDef(
            id=0x00,
            type=PilotWireMode,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        set_pilot_wire_mode = ZCLCommandDef(
            id=0x00,
            schema={"mode": PilotWireMode},
            is_manufacturer_specific=True,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer: int | None = None,
        **kwargs,
    ) -> list:
        """Write attributes to the cluster."""

        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def == LegrandCableOutletCluster.AttributeDefs.pilot_wire_mode:
                await self.set_pilot_wire_mode(value, manufacturer=manufacturer)
                await super().read_attributes([attr], manufacturer=manufacturer)
        return await super().write_attributes(attrs, manufacturer)


(
    QuirkBuilder(f" {LEGRAND}", " Cable outlet")
    .replaces(LegrandCluster)
    .replaces(LegrandCableOutletCluster)
    .enum(
        attribute_name=LegrandCluster.AttributeDefs.device_mode.name,
        cluster_id=LegrandCluster.cluster_id,
        enum_class=DeviceMode,
        translation_key="device_mode",
        fallback_name="Device mode",
    )
    .enum(
        attribute_name=LegrandCableOutletCluster.AttributeDefs.pilot_wire_mode.name,
        cluster_id=LegrandCableOutletCluster.cluster_id,
        enum_class=PilotWireMode,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot wire mode",
        entity_type=EntityType.STANDARD,
    )
    .add_to_registry()
)
