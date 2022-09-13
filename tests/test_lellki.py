"""Tests for Lellki quirks."""


import zhaquirks
import zhaquirks.lellki.wp33

zhaquirks.setup()


def test_e220_kr4n0z0_ha_signature(assert_signature_matches_quirk):
    """Test Lellki WP33 E220_KR4N0Z0_HA 4 controlled AC + 2 uncontrolled USB Power Strip."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=0, maximum_buffer_size=80, maximum_incoming_transfer_size=160, server_mask=0, maximum_outgoing_transfer_size=160, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": ["0x0000", "0x0003", "0x0004", "0x0005", "0x0006"],
                "out_clusters": ["0x0000"],
            },
            "2": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": ["0x0000", "0x0003", "0x0004", "0x0005", "0x0006"],
                "out_clusters": ["0x0000"],
            },
            "3": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": ["0x0000", "0x0003", "0x0004", "0x0005", "0x0006"],
                "out_clusters": ["0x0000"],
            },
            "4": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": ["0x0000", "0x0003", "0x0004", "0x0005", "0x0006"],
                "out_clusters": ["0x0000"],
            },
        },
        "manufacturer": " ",
        "model": "E220-KR4N0Z0-HA",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(zhaquirks.lellki.wp33.e220_kr4n0z0_ha, signature)
