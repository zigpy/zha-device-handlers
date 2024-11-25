"""NodOn pilot wire heating module."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
)
from zigpy.zdo.types import NodeDescriptor

NODON = "NodOn"
NODON_MANUFACTURER_ID = 4747
NODON_PILOT_WIRE_CLUSTER_ID = 0xFC00  # 64512

ADEO = "Adeo"
ADEO_NODE_DESCRIPTION_WITH_CORRECTED_MANUFACTURER_CODE = NodeDescriptor(
    # the values are from a real Adeo device
    logical_type=1,
    complex_descriptor_available=0,
    user_descriptor_available=0,
    reserved=0,
    aps_flags=0,
    frequency_band=8,
    mac_capability_flags=142,
    # manufacturer_code = 4727,
    manufacturer_code=NODON_MANUFACTURER_ID,
    maximum_buffer_size=82,
    maximum_incoming_transfer_size=500,
    server_mask=11264,
    maximum_outgoing_transfer_size=500,
    descriptor_capability_field=0,
)


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


class BasePilotWireCluster(CustomCluster):
    """Base cluster to set Pilot Wire mode."""

    name: str = "PilotWireCluster"
    cluster_id: t.uint16_t = NODON_PILOT_WIRE_CLUSTER_ID
    ep_attribute: str = "pilot_wire_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        pilot_wire_mode = ZCLAttributeDef(
            id=0x0000,
            type=NodOnPilotWireMode,
            # I got the following error without setting zcl_type explicitly to int:
            # Failed to write attribute pilot_wire_mode=<NodOnPilotWireMode.FrostProtection: 3>: <Status.INVALID_DATA_TYPE: 141>
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        set_pilot_wire_mode = ZCLCommandDef(
            id=0x00,
            schema={"mode": NodOnPilotWireMode},
            direction=Direction.Client_to_Server,
            is_manufacturer_specific=True,
        )


class NodOnPilotWireCluster(BasePilotWireCluster):
    """NodOn manufacturer specific cluster to set Pilot Wire mode."""

    pass


class AdeoPilotWireCluster(BasePilotWireCluster):
    """Adeo manufacturer specific cluster to set Pilot Wire mode."""

    # Adeo SIN-4-FP-21_EQU has a weird setup where it reports 4727
    # manufacturer_code in node_descriptor(), but requires NodOn's (4747)
    # manufacturer_id to execute commands and get/set attributes.

    # This seems to have no effect, but I'll still leave it here.
    # Maybe it will get fixed in future releases. NodeDescriptor magic won't
    # be necessary then.
    manufacturer_id_override: t.uint16_t = NODON_MANUFACTURER_ID


nodon = (
    QuirkBuilder(NODON, "SIN-4-FP-21")
    .replaces(NodOnPilotWireCluster)
    .enum(
        attribute_name=NodOnPilotWireCluster.AttributeDefs.pilot_wire_mode.name,
        enum_class=NodOnPilotWireMode,
        cluster_id=NodOnPilotWireCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="pilot_wire",
        fallback_name="Pilot Wire",
    )
)

adeo = (
    nodon.clone(omit_man_model_data=True)
    .applies_to(ADEO, "SIN-4-FP-21_EQU")
    .replaces(AdeoPilotWireCluster)
    # please read the comment in AdeoPilotWireCluster
    .node_descriptor(ADEO_NODE_DESCRIPTION_WITH_CORRECTED_MANUFACTURER_CODE)
)

nodon.add_to_registry()
adeo.add_to_registry()
