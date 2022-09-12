"""Tests for Feibit quirks."""


import zhaquirks
import zhaquirks.feibit.fnb56

zhaquirks.setup()


def test_zsw01lx20_signature(assert_signature_matches_quirk):
    """Test FeiBit 1 gang light switch."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4478, maximum_buffer_size=127, maximum_incoming_transfer_size=90, server_mask=10752, maximum_outgoing_transfer_size=90, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "11": {
                "profile_id": 49246,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x1000",
                ],
                "out_clusters": ["0x0019"],
            }
        },
        "manufacturer": "FeiBit",
        "model": "FNB56-ZSW01LX2.0",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(zhaquirks.feibit.fnb56.FNB56_ZSW01LX20, signature)


def test_zsw02lx20_signature(assert_signature_matches_quirk):
    """Test FeiBit 2 gang light switch."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4478, maximum_buffer_size=127, maximum_incoming_transfer_size=90, server_mask=10752, maximum_outgoing_transfer_size=90, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "11": {
                "profile_id": 49246,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x1000",
                ],
                "out_clusters": ["0x0019"],
            },
            "12": {
                "profile_id": 49246,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                ],
                "out_clusters": ["0x0019"],
            },
        },
        "manufacturer": "FeiBit",
        "model": "FNB56-ZSW02LX2.0",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(zhaquirks.feibit.fnb56.FNB56_ZSW02LX20, signature)


def test_zsw03lx20_signature(assert_signature_matches_quirk):
    """Test FeiBit 3 gang light switch."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4478, maximum_buffer_size=127, maximum_incoming_transfer_size=90, server_mask=10752, maximum_outgoing_transfer_size=90, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 49246,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x1000",
                ],
                "out_clusters": ["0x0019"],
            },
            "2": {
                "profile_id": 49246,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                ],
                "out_clusters": ["0x0019"],
            },
            "3": {
                "profile_id": 49246,
                "device_type": "0x0000",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                ],
                "out_clusters": ["0x0019"],
            },
        },
        "manufacturer": "FeiBit",
        "model": "FNB56-ZSW03LX2.0",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(zhaquirks.feibit.fnb56.FNB56_ZSW03LX20, signature)
