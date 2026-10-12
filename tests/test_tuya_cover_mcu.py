"""Tests for Tuya MCU cover quirks."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaClusterData
from zhaquirks.tuya.ts0601_cover_mcu import TuyaCoverCommand, TuyaMCUCover0601

zhaquirks.setup()


def test_signature_rmymn92d(assert_signature_matches_quirk):
    """Test TZE200_rmymn92d signature matches quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            },
            "242": {
                "profile_id": 0xA1E0,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "_TZE200_rmymn92d",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(TuyaMCUCover0601, signature)


def test_signature_r0jdjrvi(assert_signature_matches_quirk):
    """Test TZE200_r0jdjrvi signature matches quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            },
            "242": {
                "profile_id": 0xA1E0,
                "device_type": "0x0061",
                "in_clusters": [],
                "out_clusters": ["0x0021"],
            },
        },
        "manufacturer": "_TZE200_r0jdjrvi",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(TuyaMCUCover0601, signature)


@pytest.mark.parametrize(
    "command_id, expected_tuya_command",
    [
        (0x0000, TuyaCoverCommand.OPEN),
        (0x0001, TuyaCoverCommand.CLOSE),
        (0x0002, TuyaCoverCommand.STOP),
    ],
)
async def test_cover_open_close_stop(
    zigpy_device_from_quirk, command_id, expected_tuya_command
):
    """Test open, close, and stop commands."""
    device = zigpy_device_from_quirk(TuyaMCUCover0601)
    cover_cluster = device.endpoints[1].window_covering
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(tuya_cluster, "tuya_mcu_command") as mcu_cmd:
        rsp = await cover_cluster.command(command_id)

        assert rsp.status == foundation.Status.SUCCESS
        mcu_cmd.assert_called_once()

        cluster_data = mcu_cmd.call_args[0][0]
        assert isinstance(cluster_data, TuyaClusterData)
        assert cluster_data.cluster_attr == "curtain_switch"
        assert cluster_data.attr_value == expected_tuya_command
        assert cluster_data.manufacturer is None


async def test_cover_go_to_lift_percentage(zigpy_device_from_quirk):
    """Test go_to_lift_percentage command."""
    device = zigpy_device_from_quirk(TuyaMCUCover0601)
    cover_cluster = device.endpoints[1].window_covering
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(tuya_cluster, "tuya_mcu_command") as mcu_cmd:
        rsp = await cover_cluster.command(0x0005, 50)

        assert rsp.status == foundation.Status.SUCCESS
        mcu_cmd.assert_called_once()

        cluster_data = mcu_cmd.call_args[0][0]
        assert isinstance(cluster_data, TuyaClusterData)
        assert cluster_data.cluster_attr == "current_position_lift_percentage"
        assert cluster_data.attr_value == 50
        assert cluster_data.manufacturer is None


async def test_cover_unsupported_command(zigpy_device_from_quirk):
    """Test unsupported command returns error status."""
    device = zigpy_device_from_quirk(TuyaMCUCover0601)
    cover_cluster = device.endpoints[1].window_covering

    rsp = await cover_cluster.command(0x0006)
    assert rsp.status == foundation.Status.UNSUP_CLUSTER_COMMAND


async def test_cover_dp_updates(zigpy_device_from_quirk):
    """Test that DP updates propagate to the WindowCovering cluster."""
    device = zigpy_device_from_quirk(TuyaMCUCover0601)
    cover_cluster = device.endpoints[1].window_covering
    listener = ClusterListener(cover_cluster)

    # Simulate DP2 position update (current_position_lift_percentage)
    cover_cluster.update_attribute("current_position_lift_percentage", 75)
    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][1] == 75

    # Simulate DP1 curtain_switch update
    cover_cluster.update_attribute("curtain_switch", 0)
    assert len(listener.attribute_updates) == 2
    assert listener.attribute_updates[1][1] == 0
