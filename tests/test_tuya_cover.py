"""Test units for Tuya covers."""

from unittest import mock

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import ATTR_COVER_DIRECTION_SETTING, ATTR_COVER_MAIN_CONTROL
from zhaquirks.tuya.mcu import (
    CoverCommandStepDirection,
    CoverMotorStatus,
    CoverSettingLimitOperation,
    CoverSettingMotorDirection,
)
from zhaquirks.tuya.ts0601_cover import TuyaMoesCover0601

zhaquirks.setup()


@pytest.mark.parametrize(
    "command, args, kwargs, expected_frame",
    (
        # Window cover open, close, stop commands are 0, 1 & 2 respectively
        # Expected frame is a set_value command for data point 1, with an enum value of 0 for open,
        # 2 for close, 1 to stop
        (0x00, [], {}, b"\x01\x01\x00\x00\x01\x01\x04\x00\x01\x00"),
        (0x01, [], {}, b"\x01\x01\x00\x00\x01\x01\x04\x00\x01\x02"),
        (0x02, [], {}, b"\x01\x01\x00\x00\x01\x01\x04\x00\x01\x01"),
        # command #5 is go_to_lift_percentage (WindowCovering.ServerCommandDefs.go_to_lift_percentage.id)
        # expect a frame to set data point id 4 to a int value of 80 (100-20%)
        (0x05, [20], {}, b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\x50"),
        # small step open
        (
            0xF0,
            [],
            {"direction": CoverCommandStepDirection.Open},
            b"\x01\x01\x00\x00\x01\x14\x04\x00\x01\x00",
        ),
        # small step close
        (
            0xF0,
            [],
            {"direction": CoverCommandStepDirection.Close},
            b"\x01\x01\x00\x00\x01\x14\x04\x00\x01\x01",
        ),
        # open limit set
        (
            0xF1,
            [],
            {"operation": CoverSettingLimitOperation.SetOpen},
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x00",
        ),
        # close limit set
        (
            0xF1,
            [],
            {"operation": CoverSettingLimitOperation.SetClose},
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x01",
        ),
        # clear open limit clear
        (
            0xF1,
            [],
            {"operation": CoverSettingLimitOperation.ClearOpen},
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x02",
        ),
        # clear close limit clear
        (
            0xF1,
            [],
            {"operation": CoverSettingLimitOperation.ClearClose},
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x03",
        ),
        # clear both limits
        (
            0xF1,
            [],
            {"operation": CoverSettingLimitOperation.ClearBoth},
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x04",
        ),
    ),
)
async def test_cover_move_commands(
    zigpy_device_from_v2_quirk, command, args, kwargs, expected_frame
):
    """Test executing cluster move commands for tuya cover (that supports multiple data points)."""

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    cover_cluster = device.endpoints[1].window_covering

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await cover_cluster.command(command, *args, **kwargs)

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            0xEF00,
            1,
            expected_frame,
            expect_reply=True,
            command_id=0,
        )
        assert rsp.status == foundation.Status.SUCCESS


async def test_cover_unknown_command(zigpy_device_from_v2_quirk):
    """Test executing unexpected cluster command returns an unsupported status."""

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    cover_cluster = device.endpoints[1].window_covering

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        # send a command, use the max (uint8) value as an example unsupported command id
        rsp = await cover_cluster.command(0xFF)

        await wait_for_zigpy_tasks()
        m1.assert_not_called()
        assert rsp.status == foundation.Status.UNSUP_CLUSTER_COMMAND


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
async def test_cover_report_values(
    zigpy_device_from_v2_quirk, frame, cluster, attributes
):
    """Test receiving single attributes from tuya cover (that supports multiple data points)."""

    cover_dev = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = cover_dev.endpoints[1].tuya_manufacturer
    target_cluster = getattr(cover_dev.endpoints[1], cluster)
    tuya_listener = ClusterListener(target_cluster)

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert tuya_listener.attribute_updates == list(attributes.items())


async def test_cover_report_multiple_values(zigpy_device_from_v2_quirk):
    """Test receiving multiple attributes from tuya cover (that supports multiple data points)."""

    # A real packet with multiple Tuya data points 1,7,3,5 & 13 (motor status, unknown, position,
    # direction, battery)
    frame = b"\x09\x00\x02\x00\x00\x01\x04\x00\x01\x01\x07\x04\x00\x01\x01\x03\x02\x00\x04\x00\x00\x00\x14\x05\x04\x00\x01\x01\x0d\x02\x00\x04\x00\x00\x00\x5c"
    motor_status_id = ATTR_COVER_MAIN_CONTROL
    motor_status_expected = CoverMotorStatus.Stopped
    blind_open_pct_id = 0x08
    blind_open_pct_expected = (
        80  # (blind reports % closed, cluster attribute expects % open)
    )
    battery_pct_id = (
        0x21  # PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )
    motor_direction_id = ATTR_COVER_DIRECTION_SETTING
    motor_direction_expected = CoverSettingMotorDirection.Backward
    battery_pct_expected = 92 * 2  # (attribute expects 2x real percentage)

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
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

    assert (
        motor_status_id,
        motor_status_expected,
    ) in cover_listener.attribute_updates
    assert (
        blind_open_pct_id,
        blind_open_pct_expected,
    ) in cover_listener.attribute_updates
    assert (
        motor_direction_id,
        motor_direction_expected,
    ) in cover_listener.attribute_updates
    assert power_listener.attribute_updates == [(battery_pct_id, battery_pct_expected)]


@pytest.mark.parametrize(
    "name, value, expected_frame",
    (
        (
            "motor_direction",
            CoverSettingMotorDirection.Backward,
            b"\x01\x01\x00\x00\x01\x05\x04\x00\x01\x01",
        ),
    ),
)
async def test_cover_attributes_set(
    zigpy_device_from_v2_quirk, name, value, expected_frame
):
    """Test expected commands are sent when setting attributes of a tuya cover (that supports multiple data points)."""

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    cover_cluster = device.endpoints[1].window_covering

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        write_results = await cover_cluster.write_attributes({name: value})

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            0xEF00,
            1,
            expected_frame,
            expect_reply=False,
            command_id=0,
        )
        assert write_results == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]


@pytest.mark.parametrize(
    "inverted, received_frame, expected_received_value, expected_sent_frame",
    (
        # When the invert attribute is false, the value is 100-x
        (
            False,
            b"\x09\x00\x02\x00\x00\x03\x02\x00\x04\x00\x00\x00\x0a",
            90,
            b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\x0a",
        ),
        # When inverted the value is sent and received unmodified (relative to the attribute/command
        # value)
        (
            True,
            b"\x09\x00\x02\x00\x00\x03\x02\x00\x04\x00\x00\x00\x0a",
            10,
            b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\x0a",
        ),
    ),
)
async def test_cover_invert(
    zigpy_device_from_v2_quirk,
    inverted,
    received_frame,
    expected_received_value,
    expected_sent_frame,
):
    """Test tuya cover position properly honours inverted attribute when sending and receiving."""

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    cover_cluster = device.endpoints[1].window_covering
    cover_listener = ClusterListener(cover_cluster)

    # set the invert attribute to the value to be tested
    await cover_cluster.write_attributes({"cover_inverted": inverted})

    # assert we get the value we expect when processing the received frame
    blind_open_pct_id = 0x08
    hdr, args = tuya_cluster.deserialize(received_frame)
    tuya_cluster.handle_message(hdr, args)
    assert (
        blind_open_pct_id,
        expected_received_value,
    ) in cover_listener.attribute_updates

    # Now send a command to set that value and assert we send the frame we expect
    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        rsp = await cover_cluster.command(0x05, expected_received_value)

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            0xEF00,
            1,
            expected_sent_frame,
            expect_reply=True,
            command_id=0,
        )
        assert rsp.status == foundation.Status.SUCCESS


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
