"""RAMSES bridge commands, with APS delivery and identified native chunks.

Commands 0/1 retain compatibility with firmware using ASCII chunk ACKs.
Native command 2 carries message ID, sequence, total, and text. Command 3
selects native reception on the bridge. APS acknowledgements are requested
by the sender; the quirk itself does not generate application ACK traffic.
"""

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify, Ota

from zhaquirks import CustomDevice
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

RAMSES_RX_CLUSTER = 0xFC00
RAMSES_TX_CLUSTER = 0xFC01
RAMSES_NATIVE_CHUNK_COMMAND = 0x02
RAMSES_NATIVE_MODE_COMMAND = 0x03


class RamsesRXCluster(CustomCluster):
    """RAMSES RX cluster (RAMSES_RX_CLUSTER) — ESP32 -> ZHA (device-originated messages)."""

    cluster_id = RAMSES_RX_CLUSTER

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Commands that ESP32 (client) sends to coordinator (server)."""

        send_text: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=0x00,
            schema={"text": types.CharacterString},
        )

        receive_chunk: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=RAMSES_NATIVE_CHUNK_COMMAND,
            is_manufacturer_specific=False,
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
        legacy_send_text: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=0x00,
            is_manufacturer_specific=False,
            schema={"text": types.CharacterString},
        )

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

        send_chunk: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=RAMSES_NATIVE_CHUNK_COMMAND,
            is_manufacturer_specific=False,
            schema={
                "message_id": types.uint32_t,
                "sequence": types.uint8_t,
                "total": types.uint8_t,
                "text": types.CharacterString,
            },
        )

        native_mode: foundation.ZCLCommandDef = foundation.ZCLCommandDef(
            id=RAMSES_NATIVE_MODE_COMMAND,
            is_manufacturer_specific=False,
            schema={"enabled": types.Bool},
        )

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Legacy ACK commands, retained for older firmware."""

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
                DEVICE_TYPE: 0x0000,
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
                DEVICE_TYPE: 0x0000,
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


class RamsesESPSensor(RamsesESP):
    """Match the simple-sensor descriptor used by the current ESP firmware."""

    signature = {
        **RamsesESP.signature,
        ENDPOINTS: {
            10: {
                **RamsesESP.signature[ENDPOINTS][10],
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
            }
        },
    }
    replacement = {
        **RamsesESP.replacement,
        ENDPOINTS: {
            10: {
                **RamsesESP.replacement[ENDPOINTS][10],
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
            }
        },
    }


class RamsesESPOTA(RamsesESPSensor):
    """Preserve the standard OTA client advertised by OTA-capable firmware."""

    signature = {
        **RamsesESPSensor.signature,
        ENDPOINTS: {
            10: {
                **RamsesESPSensor.signature[ENDPOINTS][10],
                OUTPUT_CLUSTERS: [RAMSES_RX_CLUSTER, Ota.cluster_id],
            }
        },
    }
    replacement = {
        **RamsesESPSensor.replacement,
        ENDPOINTS: {
            10: {
                **RamsesESPSensor.replacement[ENDPOINTS][10],
                OUTPUT_CLUSTERS: [RamsesRXCluster, Ota.cluster_id],
            }
        },
    }
