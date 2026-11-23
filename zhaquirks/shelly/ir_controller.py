"""Device handler for Shelly IR Controller Gen4 ZB."""

from __future__ import annotations

from zigpy import types
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE
from zhaquirks.shelly.wifi import (
    SHELLY_WIFI_SETUP_ENDPOINT_ID,
    ShellyCustomProfileDevice,
    ShellyWiFiSetupCluster,
)

SHELLY_IR_STORAGE_CLUSTER_ID = 0xFC05

# The IR Storage cluster sits on the Shelly endpoint (239).
SHELLY_IR_STORAGE_ENDPOINT_ID = 239


class LearningStatus(types.enum8):
    """IR learning state machine values."""

    idle = 0
    learning = 1
    learned = 2
    timeout = 3
    cancelled = 4
    error = 5


class ShellyIRStorageCluster(CustomCluster):
    """Shelly manufacturer-specific IR Storage cluster (0xFC05).

    Sits on the Shelly endpoint (239). Provides:
      - Attributes for the last emitted code ID and learning status.
      - Per-endpoint on/off code assignment attributes (0x0010 / 0x0011 for
        endpoint 1, 0x0012 / 0x0013 for endpoint 2, …).
      - Server commands to manage IR devices and codes (Emit, AddDevice,
        DeleteDevice, LearnCode, CancelLearn, DeleteCode, RenameCode,
        ListCodes, ReadRawChunk).
      - Client (response) commands sent back by the firmware (DeviceAdded,
        LearnResult, CodeList, RawChunkData, CodeReceived).
    """

    cluster_id = SHELLY_IR_STORAGE_CLUSTER_ID
    name = "Shelly IR Storage"
    ep_attribute = "shelly_ir_storage"

    class AttributeDefs(BaseAttributeDefs):
        """IR Storage cluster attribute definitions."""

        last_emitted_id = ZCLAttributeDef(
            id=0x0000,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        learning_status = ZCLAttributeDef(
            id=0x0001,
            type=LearningStatus,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        enable_notifications = ZCLAttributeDef(
            id=0x0002,
            type=types.Bool,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        cluster_revision = ZCLAttributeDef(
            id=0xFFFD,
            type=types.uint16_t,
            access="r",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        # Assignment attributes: pairs of (off_code_id, on_code_id) for each
        # of the 10 IR on/off endpoints. Attr IDs start at 0x0010 and alternate
        # off/on: 0x0010=ep1_off, 0x0011=ep1_on, 0x0012=ep2_off, …
        # 0xFFFF means no code is assigned to the slot.
        ep1_off_code = ZCLAttributeDef(
            id=0x0010,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep1_on_code = ZCLAttributeDef(
            id=0x0011,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep2_off_code = ZCLAttributeDef(
            id=0x0012,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep2_on_code = ZCLAttributeDef(
            id=0x0013,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep3_off_code = ZCLAttributeDef(
            id=0x0014,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep3_on_code = ZCLAttributeDef(
            id=0x0015,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep4_off_code = ZCLAttributeDef(
            id=0x0016,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep4_on_code = ZCLAttributeDef(
            id=0x0017,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep5_off_code = ZCLAttributeDef(
            id=0x0018,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep5_on_code = ZCLAttributeDef(
            id=0x0019,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep6_off_code = ZCLAttributeDef(
            id=0x001A,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep6_on_code = ZCLAttributeDef(
            id=0x001B,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep7_off_code = ZCLAttributeDef(
            id=0x001C,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep7_on_code = ZCLAttributeDef(
            id=0x001D,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep8_off_code = ZCLAttributeDef(
            id=0x001E,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep8_on_code = ZCLAttributeDef(
            id=0x001F,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep9_off_code = ZCLAttributeDef(
            id=0x0020,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep9_on_code = ZCLAttributeDef(
            id=0x0021,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep10_off_code = ZCLAttributeDef(
            id=0x0022,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        ep10_on_code = ZCLAttributeDef(
            id=0x0023,
            type=types.uint16_t,
            access="rwp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Commands sent to the device."""

        emit = ZCLCommandDef(
            id=0x00,
            schema={"code_id": types.uint16_t, "sends": types.uint8_t},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        add_device = ZCLCommandDef(
            id=0x01,
            schema={"name": types.CharacterString},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        delete_device = ZCLCommandDef(
            id=0x02,
            schema={"device_id": types.uint16_t},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        learn_code = ZCLCommandDef(
            id=0x03,
            schema={
                "device_id": types.uint16_t,
                "name": types.CharacterString,
                "timeout": types.uint8_t,
            },
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        cancel_learn = ZCLCommandDef(
            id=0x04,
            schema={},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        delete_code = ZCLCommandDef(
            id=0x05,
            schema={"code_id": types.uint16_t},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        rename_code = ZCLCommandDef(
            id=0x06,
            schema={"code_id": types.uint16_t, "name": types.CharacterString},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        list_codes = ZCLCommandDef(
            id=0x07,
            schema={"device_id": types.uint16_t, "offset": types.uint8_t},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        read_raw_chunk = ZCLCommandDef(
            id=0x08,
            schema={"code_id": types.uint16_t, "position": types.uint16_t},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Responses sent by the device."""

        device_added = ZCLCommandDef(
            id=0x10,
            schema={"status": types.uint8_t, "device_id": types.uint16_t},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        learn_result = ZCLCommandDef(
            id=0x11,
            schema={
                "status": types.uint8_t,
                "device_id": types.uint16_t,
                "code_id": types.uint16_t,
            },
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        # The payload layout of the next two responses isn't modeled field by
        # field yet: `types.Bytes` keeps the rest of the frame instead of
        # letting zigpy drop it as trailing data.
        code_list = ZCLCommandDef(
            id=0x12,
            schema={"data": types.Bytes},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        raw_chunk_data = ZCLCommandDef(
            id=0x13,
            schema={"position": types.uint16_t, "data": types.Bytes},
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        code_received = ZCLCommandDef(
            id=0x14,
            schema={
                "code_id": types.uint16_t,
                "hold": types.uint8_t,
                "ts": types.uint32_t,
            },
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("Shelly", "IR")
    .zigpy_device_class(ShellyCustomProfileDevice)
    .replaces(ShellyWiFiSetupCluster, endpoint_id=SHELLY_WIFI_SETUP_ENDPOINT_ID)
    .replaces(ShellyIRStorageCluster, endpoint_id=SHELLY_IR_STORAGE_ENDPOINT_ID)
    .add_to_registry()
)
