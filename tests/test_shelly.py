"""Tests for Shelly quirks."""

import asyncio

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeAccess

import zhaquirks
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE
from zhaquirks.shelly.ir_controller import (
    SHELLY_IR_STORAGE_CLUSTER_ID,
    SHELLY_IR_STORAGE_ENDPOINT_ID,
    LearningStatus,
    ShellyIRStorageCluster,
)
from zhaquirks.shelly.wifi import (
    SHELLY_WIFI_SETUP_CLUSTER_ID,
    SHELLY_WIFI_SETUP_ENDPOINT_ID,
    SHELLY_WIFI_SETUP_PROFILE_ID,
    ShellyCustomProfileDevice,
    ShellyWiFiSetupCluster,
)

zhaquirks.setup()


def _attribute_report_data(
    attribute: foundation.ZCLAttributeDef, value: object
) -> bytes:
    """Build a typed ZCL attribute report payload for Shelly WiFi attributes."""

    header = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        manufacturer=SHELLY_MANUFACTURER_CODE,
        direction=foundation.Direction.Server_to_Client,
    ).serialize()
    response = foundation.Attribute(
        attrid=attribute.id,
        value=foundation.TypeValue(type=attribute.zcl_type, value=value),
    )
    command = (
        foundation.GENERAL_COMMANDS[foundation.GeneralCommand.Report_Attributes]
        .schema([response])
        .serialize()
    )
    return t.SerializableBytes(header + command).serialize()


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_setup_cluster_replaced(zigpy_device_from_v2_quirk, model) -> None:
    """Ensure Shelly relay devices expose a typed WiFi setup cluster."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    cluster = quirked.endpoints[SHELLY_WIFI_SETUP_ENDPOINT_ID].in_clusters[
        SHELLY_WIFI_SETUP_CLUSTER_ID
    ]

    assert isinstance(quirked, ShellyCustomProfileDevice)
    assert isinstance(cluster, ShellyWiFiSetupCluster)
    assert cluster.ep_attribute == "shelly_wifi_setup"
    assert cluster.find_attribute("status") == cluster.AttributeDefs.status
    assert cluster.find_attribute("ssid") == cluster.AttributeDefs.ssid
    assert cluster.AttributeDefs.status.manufacturer_code == SHELLY_MANUFACTURER_CODE
    assert cluster.AttributeDefs.dhcp.access == ZCLAttributeAccess.Read
    assert cluster.AttributeDefs.enable.access == (
        ZCLAttributeAccess.Read | ZCLAttributeAccess.Write
    )
    assert cluster.AttributeDefs.action.access == ZCLAttributeAccess.Write
    assert cluster.AttributeDefs.action.type is t.uint8_t


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_custom_profile_packet_processed(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure Shelly custom profile packets are processed as ZCL for WiFi reads."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    cluster = quirked.endpoints[SHELLY_WIFI_SETUP_ENDPOINT_ID].in_clusters[
        SHELLY_WIFI_SETUP_CLUSTER_ID
    ]

    async def deliver_packet() -> None:
        quirked.packet_received(
            t.ZigbeePacket(
                profile_id=SHELLY_WIFI_SETUP_PROFILE_ID,
                cluster_id=SHELLY_WIFI_SETUP_CLUSTER_ID,
                src_ep=SHELLY_WIFI_SETUP_ENDPOINT_ID,
                dst_ep=SHELLY_WIFI_SETUP_ENDPOINT_ID,
                data=t.SerializableBytes(
                    _attribute_report_data(
                        cluster.AttributeDefs.status,
                        t.CharacterString("got ip"),
                    )
                ),
            )
        )

    asyncio.run(deliver_packet())

    assert cluster.get("status") == "got ip"


@pytest.mark.parametrize("model", ["1PM", "2PM"])
def test_shelly_wifi_standard_profile_packet_delegated(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure standard ZHA profile packets fall through to normal zigpy parsing."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    # Standard ZHA profile packet should delegate to super()
    zha_packet = t.ZigbeePacket(
        profile_id=zha.PROFILE_ID,
        cluster_id=Basic.cluster_id,
        src_ep=1,
        dst_ep=1,
        data=t.SerializableBytes(
            _attribute_report_data(
                Basic.AttributeDefs.model,
                t.CharacterString("1PM"),
            )
        ),
    )

    hdr, rsp_key = quirked._parse_packet_header(zha_packet)

    assert hdr is not None
    assert rsp_key is not None
    assert rsp_key.endpoint_id == 1
    assert rsp_key.cluster_id == Basic.cluster_id


def test_ir_storage_cluster_replaced(zigpy_device_from_v2_quirk):
    """IR Storage cluster is replaced with ShellyIRStorageCluster on endpoint 239."""

    quirked = zigpy_device_from_v2_quirk(
        manufacturer="Shelly",
        model="IR",
        endpoint_ids=[1, SHELLY_IR_STORAGE_ENDPOINT_ID],
        cluster_ids={
            1: {},
            SHELLY_IR_STORAGE_ENDPOINT_ID: {
                SHELLY_IR_STORAGE_CLUSTER_ID: ClusterType.Server,
            },
        },
    )

    cluster = quirked.endpoints[SHELLY_IR_STORAGE_ENDPOINT_ID].in_clusters[
        SHELLY_IR_STORAGE_CLUSTER_ID
    ]
    assert isinstance(cluster, ShellyIRStorageCluster)
    assert cluster.ep_attribute == "shelly_ir_storage"


def test_ir_storage_cluster_attributes():
    """IR Storage cluster has the expected attributes with correct access and types."""

    attrs = ShellyIRStorageCluster.AttributeDefs

    assert attrs.last_emitted_id.id == 0x0000
    assert attrs.learning_status.id == 0x0001
    assert attrs.enable_notifications.id == 0x0002
    assert attrs.cluster_revision.id == 0xFFFD

    # All attributes carry the Shelly manufacturer code.
    for attr in (
        attrs.last_emitted_id,
        attrs.learning_status,
        attrs.enable_notifications,
    ):
        assert attr.manufacturer_code == SHELLY_MANUFACTURER_CODE

    # enable_notifications is writable; last_emitted_id and learning_status are read-only.
    assert ZCLAttributeAccess.Write in attrs.enable_notifications.access
    assert ZCLAttributeAccess.Write not in attrs.last_emitted_id.access
    assert ZCLAttributeAccess.Write not in attrs.learning_status.access


def test_ir_storage_assignment_attributes():
    """Assignment attributes cover all 10 on/off endpoint slots."""

    attrs = ShellyIRStorageCluster.AttributeDefs

    # Slots start at 0x0010 and increment by 2 per endpoint (off=even, on=odd).
    for ep_index in range(10):
        off_id = 0x0010 + ep_index * 2
        on_id = 0x0010 + ep_index * 2 + 1
        ep_num = ep_index + 1
        off_attr = getattr(attrs, f"ep{ep_num}_off_code")
        on_attr = getattr(attrs, f"ep{ep_num}_on_code")
        assert off_attr.id == off_id, f"ep{ep_num} off code attr id mismatch"
        assert on_attr.id == on_id, f"ep{ep_num} on code attr id mismatch"
        assert ZCLAttributeAccess.Write in off_attr.access
        assert ZCLAttributeAccess.Write in on_attr.access


def test_ir_storage_server_commands():
    """IR Storage cluster exposes all expected server-side commands."""

    cmds = ShellyIRStorageCluster.ServerCommandDefs

    assert cmds.emit.id == 0x00
    assert cmds.add_device.id == 0x01
    assert cmds.delete_device.id == 0x02
    assert cmds.learn_code.id == 0x03
    assert cmds.cancel_learn.id == 0x04
    assert cmds.delete_code.id == 0x05
    assert cmds.rename_code.id == 0x06
    assert cmds.list_codes.id == 0x07
    assert cmds.read_raw_chunk.id == 0x08

    for cmd in (
        cmds.emit,
        cmds.add_device,
        cmds.delete_device,
        cmds.learn_code,
        cmds.cancel_learn,
        cmds.delete_code,
        cmds.rename_code,
        cmds.list_codes,
        cmds.read_raw_chunk,
    ):
        assert cmd.manufacturer_code == SHELLY_MANUFACTURER_CODE


def test_ir_storage_client_commands():
    """IR Storage cluster exposes all expected client-side (response) commands."""

    cmds = ShellyIRStorageCluster.ClientCommandDefs

    assert cmds.device_added.id == 0x10
    assert cmds.learn_result.id == 0x11
    assert cmds.code_list.id == 0x12
    assert cmds.raw_chunk_data.id == 0x13
    assert cmds.code_received.id == 0x14


def test_ir_learning_status_enum():
    """LearningStatus enum matches firmware values."""

    assert int(LearningStatus.idle) == 0
    assert int(LearningStatus.learning) == 1
    assert int(LearningStatus.learned) == 2
    assert int(LearningStatus.timeout) == 3
    assert int(LearningStatus.cancelled) == 4
    assert int(LearningStatus.error) == 5
