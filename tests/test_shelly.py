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


def _ir_controller(zigpy_device_from_v2_quirk):
    """Create a quirked Shelly IR controller with its endpoint 239 clusters."""

    return zigpy_device_from_v2_quirk(
        "Shelly",
        "IR",
        endpoint_ids=[1, SHELLY_IR_STORAGE_ENDPOINT_ID],
        cluster_ids={
            SHELLY_IR_STORAGE_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
                SHELLY_IR_STORAGE_CLUSTER_ID: ClusterType.Server,
            },
        },
    )


def _deliver_custom_profile_frame(device, cluster_id: int, data: bytes) -> None:
    """Deliver a frame from endpoint 239 on Shelly's custom profile."""

    async def deliver_packet() -> None:
        device.packet_received(
            t.ZigbeePacket(
                profile_id=SHELLY_WIFI_SETUP_PROFILE_ID,
                cluster_id=cluster_id,
                src_ep=SHELLY_IR_STORAGE_ENDPOINT_ID,
                dst_ep=SHELLY_IR_STORAGE_ENDPOINT_ID,
                data=t.SerializableBytes(data),
            )
        )

    asyncio.run(deliver_packet())


def _ir_client_command_data(command: foundation.ZCLCommandDef, payload: bytes) -> bytes:
    """Build a manufacturer-specific IR Storage response frame sent by the device."""

    header = foundation.ZCLHeader.cluster(
        tsn=2,
        command_id=command.id,
        manufacturer=SHELLY_MANUFACTURER_CODE,
        direction=foundation.Direction.Server_to_Client,
    ).serialize()
    return header + payload


def test_ir_storage_cluster_replaced(zigpy_device_from_v2_quirk):
    """The IR controller gets the custom-profile device and both Shelly clusters."""

    quirked = _ir_controller(zigpy_device_from_v2_quirk)
    clusters = quirked.endpoints[SHELLY_IR_STORAGE_ENDPOINT_ID].in_clusters

    assert isinstance(quirked, ShellyCustomProfileDevice)
    assert isinstance(clusters[SHELLY_WIFI_SETUP_CLUSTER_ID], ShellyWiFiSetupCluster)
    assert isinstance(clusters[SHELLY_IR_STORAGE_CLUSTER_ID], ShellyIRStorageCluster)
    assert clusters[SHELLY_IR_STORAGE_CLUSTER_ID].ep_attribute == "shelly_ir_storage"


@pytest.mark.parametrize(
    ("attribute", "value", "expected"),
    [
        (
            ShellyIRStorageCluster.AttributeDefs.learning_status,
            t.uint8_t(2),
            LearningStatus.learned,
        ),
        (
            ShellyIRStorageCluster.AttributeDefs.ep1_on_code,
            t.uint16_t(0x0102),
            0x0102,
        ),
        (
            ShellyIRStorageCluster.AttributeDefs.cluster_revision,
            t.uint16_t(1),
            1,
        ),
    ],
)
def test_ir_storage_custom_profile_report(
    zigpy_device_from_v2_quirk, attribute, value, expected
):
    """A custom-profile report from endpoint 239 updates the IR cluster cache."""

    quirked = _ir_controller(zigpy_device_from_v2_quirk)
    cluster = quirked.endpoints[SHELLY_IR_STORAGE_ENDPOINT_ID].in_clusters[
        SHELLY_IR_STORAGE_CLUSTER_ID
    ]

    _deliver_custom_profile_frame(
        quirked,
        SHELLY_IR_STORAGE_CLUSTER_ID,
        _attribute_report_data(attribute, value),
    )

    assert cluster.get(attribute.name) == expected
    if attribute is ShellyIRStorageCluster.AttributeDefs.learning_status:
        assert isinstance(cluster.get(attribute.name), LearningStatus)


@pytest.mark.parametrize(
    ("command", "payload", "expected"),
    [
        (
            ShellyIRStorageCluster.ClientCommandDefs.learn_result,
            bytes([0x00, 0x03, 0x00, 0x07, 0x00]),
            {"status": 0, "device_id": 3, "code_id": 7},
        ),
        (
            ShellyIRStorageCluster.ClientCommandDefs.code_list,
            bytes([0x02, 0x01, 0x00, 0x02, 0x00]),
            {"data": bytes([0x02, 0x01, 0x00, 0x02, 0x00])},
        ),
        (
            ShellyIRStorageCluster.ClientCommandDefs.raw_chunk_data,
            bytes([0x40, 0x00, 0xAA, 0xBB, 0xCC, 0xDD]),
            {"position": 0x40, "data": bytes([0xAA, 0xBB, 0xCC, 0xDD])},
        ),
    ],
)
def test_ir_storage_custom_profile_command(
    zigpy_device_from_v2_quirk, command, payload, expected
):
    """Responses from endpoint 239 reach the IR cluster with their payload."""

    quirked = _ir_controller(zigpy_device_from_v2_quirk)
    cluster = quirked.endpoints[SHELLY_IR_STORAGE_ENDPOINT_ID].in_clusters[
        SHELLY_IR_STORAGE_CLUSTER_ID
    ]
    received = []

    class Listener:
        def cluster_command(self, tsn, command_id, args):
            received.append((command_id, args))

    cluster.add_listener(Listener())

    _deliver_custom_profile_frame(
        quirked,
        SHELLY_IR_STORAGE_CLUSTER_ID,
        _ir_client_command_data(command, payload),
    )

    assert len(received) == 1
    command_id, args = received[0]
    assert command_id == command.id
    assert args.as_dict() == expected
