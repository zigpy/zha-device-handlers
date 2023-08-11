"""Tests the Danfoss quirk (all tests were written for the Popp eT093WRO)"""
from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.danfoss.thermostat import DanfossTRVCluster

zhaquirks.setup()


def test_popp_signature(assert_signature_matches_quirk):
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4678, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=769, device_version=1, input_clusters=[0, 1, 3, 10, 32, 513, 516, 2821], output_clusters=[0, 25])
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0301",
                "in_clusters": ["0x0000", "0x0001", "0x0003", "0x000a", "0x0020", "0x0201", "0x0204", "0x0b05"],
                "out_clusters": ["0x0000", "0x0019"]
            }
        },
        "manufacturer": "D5X84YU",
        "model": "eT093WRO",
        "class": "danfoss.thermostat.DanfossThermostat"
    }

    assert_signature_matches_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat, signature)


async def test_danfoss_trv_read_attributes(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)

    danfoss_thermostat_cluster = device.endpoints[1].in_clusters[Thermostat.cluster_id]
    danfoss_trv_cluster = device.endpoints[1].in_clusters[DanfossTRVCluster.cluster_id]

    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr, foundation.Status.SUCCESS, foundation.TypeValue(None, 6)
            )
            for attr in attributes
        ]
        return (records,)

    # data is served from danfoss_thermostat
    patch_danfoss_thermostat_read = mock.patch.object(
        danfoss_thermostat_cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    )

    with patch_danfoss_thermostat_read:
        # data should be received from danfoss_trv
        success, fail = await danfoss_trv_cluster.read_attributes(["open_window_detection"])
        assert success
        assert 6 in success.values()
        assert not fail

        # this should return occupied_heating_setpoint_scheduled and occupied_heating_setpoint
        success, fail = await danfoss_trv_cluster.read_attributes(["occupied_heating_setpoint_scheduled"])
        assert success
        assert 6 in success.values()
        assert not fail