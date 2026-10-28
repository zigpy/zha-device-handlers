"""RAMSES bridge commands, with APS delivery and identified native chunks.

Commands 0/1 retain compatibility with firmware using ASCII chunk ACKs.
Native command 2 carries message ID, sequence, total, and text. Command 3
selects native reception on the bridge. APS acknowledgements are requested
by the sender; the quirk itself does not generate application ACK traffic.
"""

from zigpy import types
from zigpy.zcl import ClusterType, foundation

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


class RamsesRXCluster(CustomCluster):
    """RAMSES RX cluster (0xFC00): ESP32 to ZHA device-originated messages."""

    cluster_id = 0xFC00

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Commands that ESP32 (client) sends to coordinator (server)."""

        send_text = foundation.ZCLCommandDef(
            id=0x00,
            schema={"text": types.CharacterString},
        )

        receive_chunk = foundation.ZCLCommandDef(
            id=0x02,
            manufacturer_code=None,
            schema={
                "message_id": types.uint32_t,
                "sequence": types.uint8_t,
                "total": types.uint8_t,
                "text": types.CharacterString,
            },
        )

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Legacy commands; native delivery does not use ASCII ACKs."""

        # Existing firmware sent command 0 with client-to-server direction.
        # Decode that wire format as well as the ClientCommandDefs mapping.
        legacy_send_text = foundation.ZCLCommandDef(
            id=0x00,
            manufacturer_code=None,
            schema={"text": types.CharacterString},
        )

        ack_chunk = foundation.ZCLCommandDef(
            id=0x01,
            schema={"text": types.CharacterString},
        )


class RamsesTXCluster(CustomCluster):
    """RAMSES TX cluster (0xFC01): ZHA to ESP32 coordinator messages."""

    cluster_id = 0xFC01

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Client commands (from ZHA to ESP32) — the RAMSES-II message payload."""

        set_text = foundation.ZCLCommandDef(
            id=0x00,
            schema={"text": types.CharacterString},
        )

        send_chunk = foundation.ZCLCommandDef(
            id=0x02,
            manufacturer_code=None,
            schema={
                "message_id": types.uint32_t,
                "sequence": types.uint8_t,
                "total": types.uint8_t,
                "text": types.CharacterString,
            },
        )

        native_mode = foundation.ZCLCommandDef(
            id=0x03,
            manufacturer_code=None,
            schema={"enabled": types.Bool},
        )

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Legacy ACK commands, retained for older firmware."""

        ack_chunk = foundation.ZCLCommandDef(
            id=0x01,
            schema={"text": types.CharacterString},
        )


(
    QuirkBuilder("ELECRAM", "Ramses_esp32c6")
    .replaces(RamsesTXCluster, endpoint_id=10)
    .replaces(RamsesRXCluster, endpoint_id=10, cluster_type=ClusterType.Client)
    .add_to_registry()
)
