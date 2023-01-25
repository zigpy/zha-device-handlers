"""Tests for Develco/Frient A/S quirks."""

import zhaquirks.develco.motion


def test_motion_signature(assert_signature_matches_quirk):
    """Test Develco Motion Sensor Pro signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.NONE: 0>, manufacturer_code=4117, maximum_buffer_size=80, maximum_incoming_transfer_size=80, server_mask=0, maximum_outgoing_transfer_size=80, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=False, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 49353,
                "device_type": "0x0001",
                "in_clusters": ["0x0003", "0x0005", "0x0006"],
                "out_clusters": [],
            },
            "34": {
                "profile_id": 260,
                "device_type": "0x0107",
                "in_clusters": ["0x0000", "0x0003", "0x0406"],
                "out_clusters": [],
            },
            "35": {
                "profile_id": 260,
                "device_type": "0x0402",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x000f",
                    "0x0020",
                    "0x0500",
                ],
                "out_clusters": ["0x000a", "0x0019"],
            },
            "38": {
                "profile_id": 260,
                "device_type": "0x0302",
                "in_clusters": ["0x0000", "0x0003", "0x0402"],
                "out_clusters": ["0x0003"],
            },
            "39": {
                "profile_id": 260,
                "device_type": "0x0106",
                "in_clusters": ["0x0000", "0x0003", "0x0400"],
                "out_clusters": [],
            },
            "40": {
                "profile_id": 260,
                "device_type": "0x0107",
                "in_clusters": ["0x0000", "0x0003", "0x0406"],
                "out_clusters": [],
            },
            "41": {
                "profile_id": 260,
                "device_type": "0x0107",
                "in_clusters": ["0x0000", "0x0003", "0x0406"],
                "out_clusters": [],
            },
        },
        "manufacturer": "frient A/S",
        "model": "MOSZB-140",
        "class": "develco.motion.MOSZB140",
    }

    assert_signature_matches_quirk(zhaquirks.develco.motion.MOSZB140, signature)
