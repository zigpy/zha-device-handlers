"""Tests for Niko quirks."""

import zhaquirks

zhaquirks.setup()


def test_double_connectable_switch_signature(assert_signature_matches_quirk):
    """Test Niko Double Connectable switch signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4703, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x010a",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0b05",
                    "0xfc00",
                    "0xfc01",
                ],
                "out_clusters": ["0x0019"],
            },
            "2": {
                "profile_id": 260,
                "device_type": "0x010a",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0b05",
                    "0xfc00",
                    "0xfc01",
                ],
                "out_clusters": [],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "NIKO NV",
        "model": "Double connectable switch,10A",
        "class": "zhaquirks.niko.switch.NikoDoubleConnectableSwitch",
    }

    assert_signature_matches_quirk(
        zhaquirks.niko.switch.NikoDoubleConnectableSwitch, signature
    )
