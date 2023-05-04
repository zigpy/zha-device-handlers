"""Tests for Ikea Starkvind quirks."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import PM25

import zhaquirks
import zhaquirks.ikea.starkvind

zhaquirks.setup()


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


async def test_pm25_cluster_read(zigpy_device_from_quirk):
    """Test reading from PM25 cluster"""

    starkvind_device = zigpy_device_from_quirk(zhaquirks.ikea.starkvind.IkeaSTARKVIND)
    assert starkvind_device.model == "STARKVIND Air purifier"

    pm25_cluster = starkvind_device.endpoints[1].in_clusters[PM25.cluster_id]
    ikea_cluster = starkvind_device.endpoints[1].in_clusters[
        zhaquirks.ikea.starkvind.IkeaAirpurifier.cluster_id
    ]

    # Mock the read attribute to on the IkeaAirpurifier cluster
    # to always return 6 for anything.
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.SUCCESS, foundation.TypeValue(None, 6)
            )
            for attr in attributes
        ]
        return (records,)

    patch_ikeacluster_read = mock.patch.object(
        ikea_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )
    with patch_ikeacluster_read:
        # Reading "measured_value" should read the "air_quality_25pm" value from
        # the IkeaAirpurifier cluster
        success, fail = await pm25_cluster.read_attributes(["measured_value"])
        assert success
        assert 6 in success.values()
        assert not fail

        # Same call with allow_cache=True; a bug previously prevented this from working
        success, fail = await pm25_cluster.read_attributes(
            ["measured_value"], allow_cache=True
        )
        assert success
        assert 6 in success.values()
        assert not fail
