"""Test units for Tuya covers."""

from zhaquirks.tuya.ts0601_cover import (
    TuyaMoesCover0601,
    TuyaZemismartSmartCover0601_TZE284,
)


def test_ts601_moes_signature(assert_signature_matches_quirk):
    """Test TS0121 cover signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZE200_icka1clh",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(TuyaMoesCover0601, signature)


def test_ts0601_TZE284_signature(assert_signature_matches_quirk):
    """Test TS0601_TZE284 cover signature is matched to its quirk."""
    signature = {
        "node_descriptor": "<NodeDescriptor byte1=2 byte2=0 mac_capability_flags=128 manufacturer_code=4417 maximum_buffer_size=66 maximum_incoming_transfer_size=66 server_mask=10752 maximum_outgoing_transfer_size=66 descriptor_capability_field=0>",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xed00", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZE284_2gi1hy8s",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(TuyaZemismartSmartCover0601_TZE284, signature)
