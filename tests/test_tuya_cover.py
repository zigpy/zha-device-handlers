"""Test units for Tuya covers."""
from unittest import mock

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.ts0601_cover import (
    TuyaCover0601MultipleDataPoints,
    TuyaMoesCover0601,
)

zhaquirks.setup()

@pytest.mark.parametrize("command, expected_frame",
    (
        # Window cover open, close, stop commands are 0, 1 & 2 respectively
        # DP 1 should be 0 for open, 2 for close, 1 to stop
        (
            0x00,
            b'\x01\x01\x00\x00\x01\x01\x04\x00\x01\x00',
        ),
        (
            0x01,
            b'\x01\x01\x00\x00\x01\x01\x04\x00\x01\x02',
        ),
        (
            0x02,
            b'\x01\x01\x00\x00\x01\x01\x04\x00\x01\x01',
        ),
    ),
)
async def test_cover_move_commands(zigpy_device_from_quirk, command, expected_frame):
    """Test executing cluster move commands for tuya cover (that supports multiple data points)."""

    device = zigpy_device_from_quirk(
        zhaquirks.tuya.ts0601_cover.TuyaCover0601MultipleDataPoints
    )
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    cover_cluster = device.endpoints[1].window_covering

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await cover_cluster.command(command)

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            0xef00,
            1,
            expected_frame,
            expect_reply=True,
            command_id=0,
        )
        assert rsp.status == foundation.Status.SUCCESS

async def test_cover_set_position_command(zigpy_device_from_quirk):
    """Test executing cluster command to set the position for tuya cover (that supports multiple data points)."""

    device = zigpy_device_from_quirk(
        zhaquirks.tuya.ts0601_cover.TuyaCover0601MultipleDataPoints
    )
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    cover_cluster = device.endpoints[1].window_covering

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await cover_cluster.command(5, 20)

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            0xef00,
            1,
            b'\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\x50',
            expect_reply=True,
            command_id=0,
        )
        assert rsp.status == foundation.Status.SUCCESS

@pytest.mark.parametrize(
    "frame, cluster, attributes",
    (
        (  # TuyaDatapointData(dp=3, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x00\x00\x00\x14', *payload=20))
            b"\x09\x00\x02\x00\x00\x03\x02\x00\x04\x00\x00\x00\x14",
            "window_covering",
            # current_position_lift_percentage (blind reports % closed, cluster attribute expects % open)
            {0x0008: 80},
        ),
        (  # TuyaDatapointData(dp=13, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x00\x00\x00\\', *payload=92))
            b"\x09\x00\x02\x00\x00\x0d\x02\x00\x04\x00\x00\x00\x5c",
            "power",
            # battery_percentage_remaining (attribute expects 2x real percentage)
            {0x0021: 184},
        ),
    ),
)
async def test_cover_report_values(zigpy_device_from_quirk, frame, cluster, attributes):
    """Test receiving single attributes from tuya cover (that supports multiple data points)."""

    cover_dev = zigpy_device_from_quirk(
        zhaquirks.tuya.ts0601_cover.TuyaCover0601MultipleDataPoints
    )
    tuya_cluster = cover_dev.endpoints[1].tuya_manufacturer
    target_cluster = getattr(cover_dev.endpoints[1], cluster)
    tuya_listener = ClusterListener(target_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert tuya_listener.attribute_updates == list(attributes.items())


async def test_cover_report_multiple_values(zigpy_device_from_quirk):
    """Test receiving multiple attributes from tuya cover (that supports multiple data points)."""

    # A real packet with multiple Tuya data points 1,7,3,5 & 13
    frame = b"\x09\x00\x02\x00\x00\x01\x04\x00\x01\x01\x07\x04\x00\x01\x01\x03\x02\x00\x04\x00\x00\x00\x14\x05\x04\x00\x01\x01\x0d\x02\x00\x04\x00\x00\x00\x5c"
    blind_open_pct_id = 0x08
    blind_open_pct_expected = (
        80  # (blind reports % closed, cluster attribute expects % open)
    )
    battery_pct_id = (
        0x21  # PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )
    battery_pct_expected = 92 * 2  # (attribute expects 2x real percentage)

    device = zigpy_device_from_quirk(
        zhaquirks.tuya.ts0601_cover.TuyaCover0601MultipleDataPoints
    )
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    cover_cluster = device.endpoints[1].window_covering
    cover_listener = ClusterListener(cover_cluster)
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    assert len(cover_listener.cluster_commands) == 0
    assert len(cover_listener.attribute_updates) == 0
    assert len(power_listener.cluster_commands) == 0
    assert len(power_listener.attribute_updates) == 0

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    # blind cover will have an attribute update for motor direction, I only care that it
    # includes the new position
    assert len(cover_listener.attribute_updates) < 3
    assert (
        blind_open_pct_id,
        blind_open_pct_expected,
    ) in cover_listener.attribute_updates
    assert power_listener.attribute_updates == [(battery_pct_id, battery_pct_expected)]



def test_ts601_moes_signature(assert_signature_matches_quirk):
    """Test TS0121 cover signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 0x0104,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZE200_icka1clh",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }
    assert_signature_matches_quirk(TuyaMoesCover0601, signature)


def test_cover_signature_ZemiSmart_ZM25R3_TuyaCover0601MultipleDataPoints(
    assert_signature_matches_quirk,
):
    """Test Zemismart ZM25R3 matches TuyaCover0601MultipleDataPoints."""

    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0051",
                "in_clusters": ["0x0000", "0x0004", "0x0005", "0xef00"],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": "_TZE200_eevqq1uv",
        "model": "TS0601",
        "class": "zigpy.device.Device",
    }

    assert_signature_matches_quirk(
        TuyaCover0601MultipleDataPoints, signature
    )
