"""NODON module for custom device handlers."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    Direction,
    ZCLAttributeDef,
    ZCLCommandDef,
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

NODON = "NodOn"
NODON_PILOT_WIRE_CLUSTER_ID = 0xFC00  #64512

class NodOnPilotWireCluster(CustomCluster):
    """NodOn manufacturer specific cluster to set Pilot Wire mode."""

    name: str = "NodOnPilotWireCluster"
    cluster_id: t.uint16_t = NODON_PILOT_WIRE_CLUSTER_ID
    ep_attribute: str = "nodon_pilot_wire_cluster"

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
