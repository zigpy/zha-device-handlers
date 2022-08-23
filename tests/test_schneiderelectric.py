"""Tests for Schneider Electric."""
from unittest import mock

import zigpy.device
import zigpy.endpoint
import zigpy.quirks
from zigpy.zcl import foundation
import zigpy.zdo.types as zdo_t

import zhaquirks
import zhaquirks.kof.kof_mr101z

from tests.conftest import CoroutineMock

zhaquirks.setup()

Default_Response = foundation.GENERAL_COMMANDS[
    foundation.GeneralCommand.Default_Response
].schema


async def test_nhpb_shutter_1_signature(assert_signature_matches_quirk):
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "5": {
                "profile_id": 260,
                "device_type": "0x0202",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0102",
                    "0x0b05",
                ],
                "out_clusters": ["0x0019"],
            },
            "21": {
                "profile_id": 260,
                "device_type": "0x0104",
                "in_clusters": ["0x0000", "0x0003", "0x0b05", "0xff17"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0102",
                ],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "Schneider Electric",
        "model": "NHPB/SHUTTER/1",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(
        zhaquirks.schneiderelectric.shutter.NHPBShutter1, signature
    )


async def test_fls_air_link_4_signature(assert_signature_matches_quirk):
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "21": {
                "profile_id": 260,
                "device_type": "0x0104",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0020", "0xff17"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0019",
                    "0x0102",
                ],
            },
            "22": {
                "profile_id": 260,
                "device_type": "0x0104",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0xff17"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0102",
                ],
            },
            "23": {
                "profile_id": 260,
                "device_type": "0x0104",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0xff17"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0102",
                ],
            },
            "24": {
                "profile_id": 260,
                "device_type": "0x0104",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0xff17"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0102",
                ],
            },
        },
        "manufacturer": "Schneider Electric",
        "model": "FLS/AIRLINK/4",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(
        zhaquirks.schneiderelectric.switches.FLSAirlink4, signature
    )


async def test_fls_air_link_4_signature(assert_signature_matches_quirk):
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0100",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0b05",
                ],
                "out_clusters": ["0x0019"],
            },
            "21": {
                "profile_id": 260,
                "device_type": "0x0104",
                "in_clusters": ["0x0000", "0x0003", "0x0b05", "0xff17"],
                "out_clusters": [
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0x0008",
                    "0x0102",
                ],
            },
            "242": {
                "profile_id": 41440,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "Schneider Electric",
        "model": "CH10AX/SWITCH/1",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(
        zhaquirks.schneiderelectric.switches.CH10AXSwitch1, signature
    )
