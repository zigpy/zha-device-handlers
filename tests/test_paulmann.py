"""Tests for Paulmann quirks."""

import pytest

import zhaquirks.paulmann.fourbtnremote


@pytest.mark.parametrize("manufacturer", ("Paulmann LichtGmbH", "Paulmann Licht GmbH"))
def test_fourbtnremote_signature(assert_signature_matches_quirk, manufacturer):
    """Test PaulmannRemote4Btn signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4644, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0001",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0b05", "0x1000"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x0300",
                    "0x1000",
                ],
            },
            "2": {
                "profile_id": 260,
                "device_type": "0x0001",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0b05", "0x1000"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x0300",
                    "0x1000",
                ],
            },
        },
        "manufacturer": manufacturer,
        "model": "501.34",
        "class": "paulmann.fourbtnremote.PaulmannRemote4Btn",
    }

    assert_signature_matches_quirk(
        zhaquirks.paulmann.fourbtnremote.PaulmannRemote4Btn, signature
    )
