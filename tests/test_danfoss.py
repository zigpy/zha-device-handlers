"""Tests the Danfoss quirk (all tests were written for the Popp eT093WRO)"""
from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord

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
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x000a",
                    "0x0020",
                    "0x0201",
                    "0x0204",
                    "0x0b05",
                ],
                "out_clusters": ["0x0000", "0x0019"],
            }
        },
        "manufacturer": "D5X84YU",
        "model": "eT093WRO",
        "class": "danfoss.thermostat.DanfossThermostat",
    }

    assert_signature_matches_quirk(
        zhaquirks.danfoss.thermostat.DanfossThermostat, signature
    )


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
        danfoss_thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read),
    )

    with patch_danfoss_thermostat_read:
        # data should be received from danfoss_trv
        success, fail = await danfoss_trv_cluster.read_attributes(
            ["open_window_detection"]
        )
        assert success
        assert 6 in success.values()
        assert not fail

        # this should return occupied_heating_setpoint_scheduled and occupied_heating_setpoint
        success, fail = await danfoss_trv_cluster.read_attributes(
            ["occupied_heating_setpoint_scheduled"]
        )
        assert success
        assert 6 in success.values()
        assert not fail


async def test_danfoss_thermostat_write_attributes(zigpy_device_from_quirk):
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)

    danfoss_thermostat_cluster = device.endpoints[1].in_clusters[Thermostat.cluster_id]
    danfoss_trv_cluster = device.endpoints[1].in_clusters[DanfossTRVCluster.cluster_id]

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS)
            for attr in attributes
        ]
        return [records, []]

    setting = -100
    operation = -0x01

    def mock_setpoint(oper, sett, manufacturer=None):
        nonlocal operation, setting
        operation = oper
        setting = sett

    # data is written to trv
    patch_danfoss_trv_write = mock.patch.object(
        danfoss_thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )
    patch_danfoss_setpoint = mock.patch.object(
        danfoss_thermostat_cluster,
        "setpoint_command",
        mock.AsyncMock(side_effect=mock_setpoint),
    )

    with patch_danfoss_trv_write:
        # data should be written to trv, but reach thermostat
        success, fail = await danfoss_trv_cluster.write_attributes(
            {"external_open_window_detected": False}
        )
        assert success
        assert not fail
        assert not danfoss_thermostat_cluster._attr_cache[0x4003]

        with patch_danfoss_setpoint:
            # data should be received from danfoss_trv
            success, fail = await danfoss_thermostat_cluster.write_attributes(
                {"occupied_heating_setpoint": 6}
            )
            assert success
            assert not fail
            assert danfoss_thermostat_cluster._attr_cache[0x0012] == 6
            assert operation == 0x01
            assert setting == 6

            danfoss_thermostat_cluster._attr_cache[
                0x0015
            ] = 5  # min_limit is present normally

            success, fail = await danfoss_trv_cluster.write_attributes(
                {"system_mode": 0x00}
            )
            assert success
            assert not fail
            assert danfoss_thermostat_cluster._attr_cache[0x001C] == 0x00

            # setpoint to min_limit, when system_mode to off
            assert danfoss_thermostat_cluster._attr_cache[0x0012] == 5

            assert operation == 0x01
            assert setting == 5

            # scheduled should not send setpoint_command
            operation = -0x01
            setting = -100
            success, fail = await danfoss_trv_cluster.write_attributes(
                {"occupied_heating_setpoint_scheduled": 6}
            )
            assert success
            assert not fail
            assert danfoss_trv_cluster._attr_cache[0x41FF] == 6

            assert operation == -0x01
            assert setting == -100
