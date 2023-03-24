"""Tests for Adeo quirks."""

import zhaquirks.adeo.sensor_ldsenk08


def test_adeo_ldsenk08_signature(assert_signature_matches_quirk):
    """Test Adeo LDSENK08 open and vibration sensor signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4727, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0402",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0020",
                    "0x0500",
                    "0x0b05",
                ],
                "out_clusters": ["0x0019"],
            }
        },
        "manufacturer": "ADEO",
        "model": "LDSENK08",
    }

    assert_signature_matches_quirk(
        zhaquirks.adeo.sensor_ldsenk08.AdeoLdsenk08, signature
    )
