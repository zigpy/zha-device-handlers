"""Tests for Shelly quirks."""

import asyncio

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, OnOff
from zigpy.zcl.foundation import ZCLAttributeAccess

import zhaquirks
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE
from zhaquirks.shelly.wifi import (
    SHELLY_WIFI_SETUP_CLUSTER_ID,
    SHELLY_WIFI_SETUP_ENDPOINT_ID,
    SHELLY_WIFI_SETUP_PROFILE_ID,
    ShellyCustomProfileDevice,
    ShellyInputOnOffCluster,
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


@pytest.mark.parametrize("model", ["1PM", "Mini1PM", "Mini1"])
def test_shelly_input_commands_update_binary_sensor_state(
    zigpy_device_from_v2_quirk, model
) -> None:
    """Ensure firmware 2.0 input commands update the exposed input state."""

    quirked = zigpy_device_from_v2_quirk(
        "Shelly",
        model,
        endpoint_ids=[1, 2, SHELLY_WIFI_SETUP_ENDPOINT_ID],
        cluster_ids={
            2: {OnOff.cluster_id: ClusterType.Client},
            SHELLY_WIFI_SETUP_ENDPOINT_ID: {
                SHELLY_WIFI_SETUP_CLUSTER_ID: ClusterType.Server,
            },
        },
    )

    cluster = quirked.endpoints[2].out_clusters[OnOff.cluster_id]
    assert isinstance(cluster, ShellyInputOnOffCluster)

    cluster.handle_cluster_request(
        foundation.ZCLHeader.cluster(
            tsn=1,
            command_id=OnOff.ServerCommandDefs.toggle.id,
        ),
        [],
    )
    assert cluster.get(OnOff.AttributeDefs.on_off.name) is None

    for command, expected_state in (
        (OnOff.ServerCommandDefs.on, True),
        (OnOff.ServerCommandDefs.off, False),
        (OnOff.ServerCommandDefs.toggle, True),
    ):
        cluster.handle_cluster_request(
            foundation.ZCLHeader.cluster(tsn=1, command_id=command.id),
            [],
        )
        assert cluster.get(OnOff.AttributeDefs.on_off.name) is expected_state

    cluster.handle_cluster_request(
        foundation.ZCLHeader.cluster(tsn=1, command_id=0xFF),
        [],
    )
    assert cluster.get(OnOff.AttributeDefs.on_off.name) is True

    (metadata,) = (
        quirked._quirk_registry_entry.zha_device_factory.quirk_definition.entity_metadata
    )
    assert metadata.entity_platform.value == "binary_sensor"
    assert metadata.entity_type.value == "standard"
    assert metadata.endpoint_id == 2
    assert metadata.cluster_id == OnOff.cluster_id
    assert metadata.cluster_type is ClusterType.Client
    assert metadata.attribute_name == OnOff.AttributeDefs.on_off.name


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
