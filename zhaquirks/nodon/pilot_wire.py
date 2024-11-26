"""NodOn pilot wire heating module."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

NODON = "NodOn"
NODON_MANUFACTURER_ID = 4747
NODON_PILOT_WIRE_CLUSTER_ID = 0xFC00  # 64512
ADEO = "Adeo"


class NodOnPilotWireMode(t.enum8):
    """Pilot wire mode."""

    # Codes taken from
    # https://github.com/Koenkk/zigbee-herdsman-converters/blob/0f4833340a20db3dae625a61c41d9be0a6f952be/src/converters/fromZigbee.ts#L5285.

    Off = 0x00
    Comfort = 0x01
    Eco = 0x02
    FrostProtection = 0x03
    ComfortMinus1 = 0x04
    ComfortMinus2 = 0x05


class NodOnPilotWireCluster(CustomCluster):
    """NodOn manufacturer specific cluster to set Pilot Wire mode."""

    name: str = "PilotWireCluster"
    cluster_id: t.uint16_t = NODON_PILOT_WIRE_CLUSTER_ID
    ep_attribute: str = "pilot_wire_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        pilot_wire_mode = ZCLAttributeDef(
            id=0x0000,
            type=NodOnPilotWireMode,
            # need to explicitly set ZCL type
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )


class AdeoPilotWireCluster(NodOnPilotWireCluster):
    """Adeo manufacturer specific cluster to set Pilot Wire mode."""

    # Adeo SIN-4-FP-21_EQU has a weird setup where it reports 4727
    # manufacturer_code in node_descriptor(), but requires NodOn's (4747)
    # manufacturer_id to execute commands and get/set attributes.
    manufacturer_id_override: t.uint16_t = NODON_MANUFACTURER_ID


nodon = (
    QuirkBuilder(NODON, "SIN-4-FP-21")
    .replaces(NodOnPilotWireCluster)
)  # fmt: skip

adeo = (
    nodon.clone(omit_man_model_data=True)
    .applies_to(ADEO, "SIN-4-FP-21_EQU")
    .replaces(AdeoPilotWireCluster)
)

nodon.add_to_registry()
adeo.add_to_registry()
