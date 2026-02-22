"""Device handler for RAMSES ESP32-C6 Zigbee."""

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify

from zhaquirks.const import (
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

RAMSES_RX_CLUSTER = 0xFC00
RAMSES_TX_CLUSTER = 0xFC01


class RamsesRXCluster(CustomCluster):
    """RAMSES RX cluster (RAMSES_RX_CLUSTER) — ESP32 -> ZHA (device-originated messages)."""

    cluster_id = RAMSES_RX_CLUSTER

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Commands that ESP32 (client) sends to coordinator (server)."""

        send_text: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=0x00,
            schema={"text": types.CharacterString},
        )

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Server commands (ACKs) sent in response to `send_text` messages."""

        ack_chunk: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=0x01,
            schema={"text": types.CharacterString},
        )


class RamsesTXCluster(CustomCluster):
    """RAMSES TX cluster (RAMSES_TX_CLUSTER) — ZHA -> ESP32 (coordinator-originated messages)."""

    cluster_id = RAMSES_TX_CLUSTER

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Client commands (from ZHA to ESP32) — the RAMSES-II message payload."""

        set_text: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=0x00,
            schema={"text": types.CharacterString},
        )

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Server commands (ACKs) sent by the ESP32 in response to `set_text`."""

        ack_chunk: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=0x01,
            schema={"text": types.CharacterString},
        )


class RamsesESP(CustomDevice):
    """Ramses ESP32-C6 Zigbee."""

    signature = {
        MODELS_INFO: [
            ("ELECRAM", "Ramses_esp32c6"),
        ],
        ENDPOINTS: {
            10: {
                PROFILE_ID: zha.PROFILE_ID,  # Home Automation
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    RAMSES_TX_CLUSTER,  # Ramses TX Cluster (server - receives commands from ZHA)
                ],
                OUTPUT_CLUSTERS: [
                    RAMSES_RX_CLUSTER,  # Ramses RX Cluster (client - sends commands to ZHA)
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            10: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    RamsesTXCluster,
                ],
                OUTPUT_CLUSTERS: [
                    RamsesRXCluster,
                ],
            }
        },
    }
