"""Tests for the ELECRAM RAMSES ESP32-C6 quirk."""

import zhaquirks
from zhaquirks.elecram.ramses_esp import (
    RAMSES_RX_CLUSTER,
    RAMSES_TX_CLUSTER,
    RamsesESP,
    RamsesRXCluster,
    RamsesTXCluster,
)

zhaquirks.setup()


def test_ramses_esp_signature(assert_signature_matches_quirk):
    """Test that the RamsesESP signature matches the real device fingerprint."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=0, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=0, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "10": {
                "profile_id": 260,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",  # Basic
                    "0x0003",  # Identify
                    "0xfc01",  # RAMSES_TX_CLUSTER
                ],
                "out_clusters": [
                    "0xfc00",  # RAMSES_RX_CLUSTER
                ],
            },
        },
        "manufacturer": "ELECRAM",
        "model": "Ramses_esp32c6",
        "class": "elecram.ramses_esp.RamsesESP",
    }

    assert_signature_matches_quirk(RamsesESP, signature)


def test_ramses_esp_clusters(zigpy_device_from_quirk):
    """Test that the quirk replaces the custom clusters correctly."""

    device = zigpy_device_from_quirk(RamsesESP)

    ep = device.endpoints[10]

    # Replacement input cluster: RamsesTXCluster instead of bare 0xfc01
    assert RAMSES_TX_CLUSTER in ep.in_clusters
    assert isinstance(ep.in_clusters[RAMSES_TX_CLUSTER], RamsesTXCluster)

    # Replacement output cluster: RamsesRXCluster instead of bare 0xfc00
    assert RAMSES_RX_CLUSTER in ep.out_clusters
    assert isinstance(ep.out_clusters[RAMSES_RX_CLUSTER], RamsesRXCluster)


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
