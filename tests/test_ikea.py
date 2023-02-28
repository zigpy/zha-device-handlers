"""Tests for Ikea Starkvind quirks."""

import zhaquirks.ikea.starkvind
import zhaquirks.ikea.symfonisk


def test_ikea_starkvind(assert_signature_matches_quirk):
    """Test new 'STARKVIND Air purifier table' signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4476, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0007",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0202",
                    "0xfc57",
                    "0xfc7d",
                ],
                "out_clusters": ["0x0019", "0x0400", "0x042a"],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "IKEA of Sweden",
        "model": "STARKVIND Air purifier",
        "class": "ikea.starkvind.IkeaSTARKVIND",
    }

    assert_signature_matches_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND, signature)


def test_ikea_starkvind_v2(assert_signature_matches_quirk):
    """Test new 'STARKVIND Air purifier table' signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4476, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0007",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0202",
                    "0xfc57",
                    "0xfc7c",
                    "0xfc7d",
                ],
                "out_clusters": ["0x0019", "0x0400", "0x042a"],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "IKEA of Sweden",
        "model": "STARKVIND Air purifier table",
        "class": "ikea.starkvind.IkeaSTARKVIND_v2",
    }

    assert_signature_matches_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND_v2, signature)


def test_ikea_sound_remote_gen2_v1(assert_signature_matches_quirk):
    """Test new 'SYMFONISK sound remote gen2' with V1.0.012 signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4476, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0006",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0020",
                    "0x1000",
                    "0xfc57",
                ],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x1000",
                    "0xfc7f",
                ],
            }
        },
        "manufacturer": "IKEA of Sweden",
        "model": "SYMFONISK sound remote gen2",
        "class": "ikea.symfonisk.IkeaSYMFONISKRemoteGen2V1",
    }

    assert_signature_matches_quirk(
        zhaquirks.ikea.symfonisk.IkeaSYMFONISKRemoteGen2V1, signature
    )
