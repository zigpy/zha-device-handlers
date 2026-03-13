"""
EpsilonRT pilot wire heating module quirk.

This is a DIY project. The manufacturer ID (0x1234) is used for 
development and non-commercial purposes.

Firmware and documentation:
https://github.com/epsilonrt/ZigbeePilotWireControl
"""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

EPSILONRT = "EpsilonRT"
# Manufacturer ID 0x1234 is used by EpsilonRT DIY modules.
EPSILONRT_MANUFACTURER_ID = 0x1234
EPSILONRT_PILOT_WIRE_CLUSTER_ID = 0xFC00  # 64512
EPSILONRT_PILOT_WIRE_MODEL = "ERT-MPZ-03"

class EpsilonRTPilotWireMode(t.enum8):
    """Pilot wire mode enum (PascalCase for current ZHA compatibility)."""
    Off = 0x00
    Comfort = 0x01
    Eco = 0x02
    FrostProtection = 0x03
    ComfortMinus1 = 0x04
    ComfortMinus2 = 0x05

class EpsilonRTPilotWireCluster(CustomCluster):
    """EpsilonRT manufacturer specific cluster to control Pilot Wire mode."""

    name: str = "PilotWireCluster"
    cluster_id: t.uint16_t = EPSILONRT_PILOT_WIRE_CLUSTER_ID
    manufacturer_id_override: t.uint16_t = EPSILONRT_MANUFACTURER_ID
    ep_attribute: str = "pilot_wire_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the Pilot Wire cluster."""
        pilot_wire_mode = ZCLAttributeDef(
            id=0x0000,
            type=EpsilonRTPilotWireMode,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )

# Quirk Registration
(
    QuirkBuilder(EPSILONRT, EPSILONRT_PILOT_WIRE_MODEL)
    .replaces(EpsilonRTPilotWireCluster)
    .enum(
        attribute_name=EpsilonRTPilotWireCluster.AttributeDefs.pilot_wire_mode.name,
        enum_class=EpsilonRTPilotWireMode,
        cluster_id=EpsilonRTPilotWireCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot wire mode",
    )
    .add_to_registry()
)