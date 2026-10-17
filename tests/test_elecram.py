"""Tests for the ELECRAM RAMSES ESP32-C6 quirk."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from zigpy.zcl.clusters.general import Ota

import zhaquirks
from zhaquirks.elecram.ramses_esp import (
    RAMSES_RX_CLUSTER,
    RAMSES_TX_CLUSTER,
    RamsesESP,
    RamsesESPOTA,
    RamsesESPSensor,
    RamsesRXCluster,
    RamsesTXCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    "quirk,device_type",
    [(RamsesESP, 0x0000), (RamsesESPSensor, 0x000C), (RamsesESPOTA, 0x000C)],
)
def test_ramses_esp_signature(assert_signature_matches_quirk, quirk, device_type):
    """Test that the RamsesESP signature matches the real device fingerprint."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=0, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=0, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "10": {
                "profile_id": 260,
                "device_type": f"0x{device_type:04x}",
                "in_clusters": [
                    "0x0000",  # Basic
                    "0x0003",  # Identify
                    "0xfc01",  # RAMSES_TX_CLUSTER
                ],
                "out_clusters": [
                    "0xfc00",  # RAMSES_RX_CLUSTER
                    *(["0x0019"] if quirk is RamsesESPOTA else []),
                ],
            },
        },
        "manufacturer": "ELECRAM",
        "model": "Ramses_esp32c6",
        "class": "elecram.ramses_esp.RamsesESP",
    }

    assert_signature_matches_quirk(quirk, signature)


@pytest.mark.parametrize("quirk", [RamsesESP, RamsesESPSensor])
def test_ramses_esp_clusters(zigpy_device_from_quirk, quirk):
    """Test that the quirk replaces the custom clusters correctly."""

    device = zigpy_device_from_quirk(quirk)

    ep = device.endpoints[10]

    # Replacement input cluster: RamsesTXCluster instead of bare 0xfc01
    assert RAMSES_TX_CLUSTER in ep.in_clusters
    assert isinstance(ep.in_clusters[RAMSES_TX_CLUSTER], RamsesTXCluster)

    # Replacement output cluster: RamsesRXCluster instead of bare 0xfc00
    assert RAMSES_RX_CLUSTER in ep.out_clusters
    assert isinstance(ep.out_clusters[RAMSES_RX_CLUSTER], RamsesRXCluster)


def test_ramses_ota_cluster_preserved(zigpy_device_from_quirk):
    """OTA firmware must retain a real standard OTA output cluster."""
    device = zigpy_device_from_quirk(RamsesESPOTA)
    assert isinstance(device.endpoints[10].out_clusters[Ota.cluster_id], Ota)


def test_ramses_rx_cluster_commands():
    """Test that RamsesRXCluster defines the expected commands."""

    # Client command 0x00: send_text
    assert hasattr(RamsesRXCluster.ClientCommandDefs, "send_text")
    assert RamsesRXCluster.ClientCommandDefs.send_text.id == 0x00

    # Server command 0x01: ack_chunk
    assert hasattr(RamsesRXCluster.ServerCommandDefs, "ack_chunk")
    assert RamsesRXCluster.ServerCommandDefs.ack_chunk.id == 0x01


def test_ramses_tx_cluster_commands():
    """Test that RamsesTXCluster defines the expected commands."""

    # Client command 0x00: set_text (ZHA -> ESP32)
    assert hasattr(RamsesTXCluster.ClientCommandDefs, "set_text")
    assert RamsesTXCluster.ClientCommandDefs.set_text.id == 0x00

    # Server command 0x01: ack_chunk (ESP32 -> ZHA ACK)
    assert hasattr(RamsesTXCluster.ServerCommandDefs, "ack_chunk")
    assert RamsesTXCluster.ServerCommandDefs.ack_chunk.id == 0x01


def test_native_receive_wire_format(zigpy_device_from_quirk):
    """Decode the exact native frame emitted by the ESP APS request."""
    device = zigpy_device_from_quirk(RamsesESP)
    cluster = device.endpoints[10].out_clusters[RAMSES_RX_CLUSTER]
    # ZCL server-to-client, default response disabled, TSN 7, command 2;
    # uint32 ID, seq, total, char-string payload.
    hdr, args = cluster.deserialize(b"\x19\x07\x02\x78\x56\x34\x12\x01\x02\x05hello")
    assert hdr.frame_control.disable_default_response
    assert hdr.command_id == 2
    assert tuple(args) == (0x12345678, 1, 2, "hello")


@pytest.mark.asyncio
async def test_native_send_requests_aps_without_ascii_ack(zigpy_device_from_quirk):
    """Serialize the native command using the actual quirk's schema."""
    device = zigpy_device_from_quirk(RamsesESP)
    cluster = device.endpoints[10].in_clusters[RAMSES_TX_CLUSTER]
    endpoint = MagicMock()
    endpoint.device.get_sequence.return_value = 7
    endpoint.reply = AsyncMock()
    cluster._endpoint = endpoint
    await cluster.client_command(
        2,
        0x12345678,
        1,
        2,
        "hello",
        expect_reply=False,
        ask_for_ack=True,
        disable_default_response=True,
    )
    kwargs = endpoint.reply.call_args.kwargs
    assert kwargs["data"] == b"\x11\x07\x02\x78\x56\x34\x12\x01\x02\x05hello"
    assert kwargs["ask_for_ack"] is True
    assert kwargs["expect_reply"] is False


def test_legacy_receive_direction_still_decodes(zigpy_device_from_quirk):
    """Keep accepting command 0 sent by already deployed firmware."""
    device = zigpy_device_from_quirk(RamsesESP)
    cluster = device.endpoints[10].out_clusters[RAMSES_RX_CLUSTER]
    hdr, args = cluster.deserialize(b"\x11\x07\x00\x05hello")
    assert hdr.command_id == 0
    assert args.text == "hello"


def test_native_mode_command_schema():
    """Mode selection carries a boolean, without ASCII handshake text."""
    command = RamsesTXCluster.ClientCommandDefs.native_mode
    assert command.id == 3
    assert command.schema(enabled=True).serialize() == b"\x01"
