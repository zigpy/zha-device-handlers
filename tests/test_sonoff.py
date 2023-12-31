"""Tests for Sonoff quirks."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import AnalogOutput, BinaryInput
from zigpy.zcl.clusters.measurement import OccupancySensing

import zhaquirks
import zhaquirks.sonoff.snzb01p
import zhaquirks.sonoff.snzb06p

from tests.common import ClusterListener

zhaquirks.setup()


def test_sonoff_snzb01p(assert_signature_matches_quirk):
    """Test 'Sonoff SNZB-01P smart button' signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4742, maximum_buffer_size=82, maximum_incoming_transfer_size=255, server_mask=11264, maximum_outgoing_transfer_size=255, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0000",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x0020", "0xfc57"],
                "out_clusters": ["0x0003", "0x0006", "0x0019"],
            }
        },
        "manufacturer": "eWeLink",
        "model": "SNZB-01P",
        "class": "sonoff.snzb01p.SonoffSmartButtonSNZB01P",
    }

    assert_signature_matches_quirk(
        zhaquirks.sonoff.snzb01p.SonoffSmartButtonSNZB01P, signature
    )


def test_sonoff_snzb06p(assert_signature_matches_quirk):
    """Test 'Sonoff SNZB-06P presence sensor' signature is matched to its quirk."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4742, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0107",
                "in_clusters": [
                    "0x0000",
                    "0x0003",
                    "0x0406",
                    "0x0500",
                    "0xfc11",
                    "0xfc57",
                ],
                "out_clusters": ["0x0003", "0x0019"],
            }
        },
        "manufacturer": "SONOFF",
        "model": "SNZB-06P",
        "class": "sonoff.snzb06p.SonoffPresenceSensorSNZB06P",
    }

    assert_signature_matches_quirk(
        zhaquirks.sonoff.snzb06p.SonoffPresenceSensorSNZB06P, signature
    )


async def test_sonoff_snzb06p_occupancy_timeout(zigpy_device_from_quirk):
    """Test SNZB-06P occupancy timeout cluster."""

    device = zigpy_device_from_quirk(
        zhaquirks.sonoff.snzb06p.SonoffPresenceSensorSNZB06P
    )
    occupancy_timeout_cluster = device.endpoints[0x2].in_clusters[
        AnalogOutput.cluster_id
    ]
    occupancy_sensing_cluster = device.endpoints[0x1].in_clusters[
        OccupancySensing.cluster_id
    ]

    # Check mandatory attributes
    succ, fail = await occupancy_timeout_cluster.read_attributes(
        (
            "max_present_value",
            "min_present_value",
            "resolution",
            "application_type",
            "engineering_units",
        )
    )
    assert succ["max_present_value"] == 65535
    assert succ["min_present_value"] == 15
    assert succ["resolution"] == 1.0
    assert succ["application_type"] == 0x000E0001
    assert succ["engineering_units"] == 73

    occ_timeout_write = mock.patch.object(
        occupancy_timeout_cluster,
        "_write_attributes",
        mock.AsyncMock(
            return_value=(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
            )
        ),
    )

    occ_sensing_write = mock.patch.object(
        occupancy_sensing_cluster,
        "_write_attributes",
        mock.AsyncMock(
            return_value=(
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
            )
        ),
    )

    occupancy_sensing_listener = ClusterListener(occupancy_sensing_cluster)

    # testing double-link nature of clusters (AnalogOutput exists just to provide
    # means for configuring the setting
    with occ_timeout_write, occ_sensing_write:
        await occupancy_timeout_cluster.write_attributes({"present_value": 30})
        assert len(occupancy_timeout_cluster._write_attributes.mock_calls) == 0
        assert len(occupancy_sensing_cluster._write_attributes.mock_calls) == 1
        occupancy_timeout_cluster._write_attributes.reset_mock()
        occupancy_sensing_cluster._write_attributes.reset_mock()

        assert occupancy_sensing_listener.attribute_updates[0] == (
            zhaquirks.sonoff.snzb06p.ATTR_ULTRASONIC_O_TO_U_DELAY,
            30,
        )  # Opple system_mode

        occupancy_sensing_cluster.update_attribute(
            zhaquirks.sonoff.snzb06p.ATTR_ULTRASONIC_O_TO_U_DELAY, 15
        )
        success, fail = await occupancy_timeout_cluster.read_attributes(
            ["present_value"]
        )
        assert success
        assert 15 in success.values()
        assert not fail


async def test_sonoff_snzb06p_illuminance_level_sensing(zigpy_device_from_quirk):
    """Test SNZB-06P artificial illuminance level sensing cluster."""

    device = zigpy_device_from_quirk(
        zhaquirks.sonoff.snzb06p.SonoffPresenceSensorSNZB06P
    )
    illuminance_cluster = device.endpoints[0x2].in_clusters[BinaryInput.cluster_id]
    sonoff_cluster = device.endpoints[0x1].in_clusters[
        zhaquirks.sonoff.snzb06p.SONOFF_CLUSTER_ID_2
    ]

    sonoff_cluster.update_attribute(
        zhaquirks.sonoff.snzb06p.ATTR_SONOFF_ILLUMINATION_STATUS, 0
    )
    success, fail = await illuminance_cluster.read_attributes(["present_value"])
    assert success
    assert False in success.values()
    assert not fail

    sonoff_cluster.update_attribute(
        zhaquirks.sonoff.snzb06p.ATTR_SONOFF_ILLUMINATION_STATUS, 1
    )
    success, fail = await illuminance_cluster.read_attributes(["present_value"])
    assert success
    assert True in success.values()
    assert not fail
