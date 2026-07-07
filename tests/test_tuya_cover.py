"""Test units for Tuya covers."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaWindowCovering
from zhaquirks.tuya.ts0601_cover import (
    BorderSetting,
    MotorDirection,
    SmallStep,
    TuyaMoesCover0601,
)

zhaquirks.setup()


class AnyTSNTuyaFrame:
    """Match a Tuya DP frame, but ignore the two sequence numbers it contains.

    Most tests only receive a single packet and can match against sequence number 1. Some commands
    (e.g. go_to_lift_percentage) write to multiple DPs so we don't want to depend on the sequence
    numbers in the responses.
    """

    def __init__(self, frame: bytes) -> None:
        """Initialize with a byte array."""
        self._frame = frame

    def __eq__(self, other: object) -> bool:
        """Compare with byte array, ignoring sequence numbers at index 1 & 4."""
        if not isinstance(other, (bytes, bytearray)):
            return NotImplemented
        if len(other) < 5 or len(self._frame) < 5:
            return other == self._frame
        return (
            other[0:1] == self._frame[0:1]  # ZCL frame control
            and other[2:4] == self._frame[2:4]  # ZCL command ID + TuyaCommand status
            and other[5:] == self._frame[5:]  # DP data
        )

    def __hash__(self) -> int:
        """Return a hash of this object."""
        return hash(self._frame)

    def __repr__(self) -> str:
        """Return a string representation of the frame."""
        return f"AnyTSNTuyaFrame({self._frame!r})"


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


async def test_zemismart_zm16b_quirk(zigpy_device_from_v2_quirk):
    """Test Zemismart ZM16B cover motor v2 quirk."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    assert isinstance(quirked, CustomZigpyDevice)

    ep = quirked.endpoints[1]

    # Verify clusters are present
    cover_cluster = ep.window_covering
    assert cover_cluster is not None
    assert isinstance(cover_cluster, TuyaWindowCovering)

    tuya_cluster = ep.tuya_manufacturer
    assert tuya_cluster is not None
    assert isinstance(tuya_cluster, TuyaMCUCluster)


async def test_zemismart_zm16b_position_report(zigpy_device_from_v2_quirk):
    """Test that incoming position DP reports update the cover position."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering
    cover_listener = ClusterListener(cover_cluster)

    tuya_cluster = ep.tuya_manufacturer

    # Simulate device reporting position 75 (75% open) via DP 8
    # Should convert to ZCL 25% (0%=open, 100%=closed)
    tuya_cluster.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[TuyaDatapointData(8, TuyaData(75))],
        )
    )

    assert (
        cover_cluster.get(
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        == 25
    )

    # Verify attribute update event was fired
    assert len(cover_listener.attribute_updates) == 1
    assert (
        cover_listener.attribute_updates[0][0]
        == WindowCovering.AttributeDefs.current_position_lift_percentage.id
    )
    assert cover_listener.attribute_updates[0][1] == 25

    # Test DP 9 also updates position (position control echo)
    tuya_cluster.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=2,
            datapoints=[TuyaDatapointData(9, TuyaData(0))],
        )
    )

    assert (
        cover_cluster.get(
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        == 100
    )


async def test_zemismart_zm16b_open_command(zigpy_device_from_v2_quirk):
    """Test that the open command sends the correct DP value."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering
    tuya_cluster = ep.tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await cover_cluster.command(WindowCovering.ServerCommandDefs.up_open.id)
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        # Verify the DP 1 command was sent with Open=0
        call_data = req_mock.call_args[1]["data"]
        # The payload contains DP 1 with value 0 (Open)
        assert b"\x01" in call_data  # DP ID 1
        assert call_data[-1:] == b"\x00"  # Value = Open (0)


async def test_zemismart_zm16b_close_command(zigpy_device_from_v2_quirk):
    """Test that the close command sends the correct DP value."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering
    tuya_cluster = ep.tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await cover_cluster.command(WindowCovering.ServerCommandDefs.down_close.id)
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        call_data = req_mock.call_args[1]["data"]
        # The payload contains DP 1 with value 2 (Close)
        assert b"\x01" in call_data  # DP ID 1
        assert call_data[-1:] == b"\x02"  # Value = Close (2)


async def test_zemismart_zm16b_stop_command(zigpy_device_from_v2_quirk):
    """Test that the stop command sends the correct DP value."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering
    tuya_cluster = ep.tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await cover_cluster.command(WindowCovering.ServerCommandDefs.stop.id)
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        call_data = req_mock.call_args[1]["data"]
        # The payload contains DP 1 with value 1 (Stop)
        assert b"\x01" in call_data  # DP ID 1
        assert call_data[-1:] == b"\x01"  # Value = Stop (1)


async def test_zemismart_zm16b_go_to_lift_percentage(zigpy_device_from_v2_quirk):
    """Test that go_to_lift_percentage sends correct inverted position."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering
    tuya_cluster = ep.tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        # Send ZCL go_to_lift_percentage with 25% (25% closed = 75% open)
        await cover_cluster.command(
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id, 25
        )
        await wait_for_zigpy_tasks()

        # Should send inverted value (100 - 25 = 75) to device
        # Multiple calls expected (DP 8 and DP 9 both mapped)
        assert req_mock.call_count >= 1
        # Check that at least one call has the correct position value
        found_correct_position = False
        for call in req_mock.call_args_list:
            call_data = call[1]["data"]
            # DP 9 (position control) with value 75
            if b"\x09" in call_data and b"\x00\x00\x00\x4b" in call_data:
                found_correct_position = True
        assert found_correct_position, "Expected DP 9 with value 75 in sent data"


async def test_zemismart_zm16b_battery_report(zigpy_device_from_v2_quirk):
    """Test that battery DP reports update the battery percentage."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_3mzb0sdz", "TS0601")
    ep = quirked.endpoints[1]

    tuya_cluster = ep.tuya_manufacturer

    # Simulate device reporting battery 85% via DP 13
    tuya_cluster.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=3,
            datapoints=[TuyaDatapointData(13, TuyaData(85))],
        )
    )

    # Battery percentage should be scaled by 2 (default tuya_battery scale)
    power_cluster = ep.power
    assert power_cluster.get("battery_percentage_remaining") == 170


@pytest.mark.parametrize(
    "command_name, command_id, args, expected_frame",
    (
        # Window cover open, close, stop commands are 0, 1 & 2 respectively
        # Expected frame is a set_value command for data point 1, with an enum value of 0 for open,
        # 2 for close, 1 to stop
        ("up_open", 0x00, None, b"\x01\x01\x00\x00\x01\x01\x04\x00\x01\x00"),
        ("down_close", 0x01, None, b"\x01\x01\x00\x00\x01\x01\x04\x00\x01\x02"),
        ("stop", 0x02, None, b"\x01\x01\x00\x00\x01\x01\x04\x00\x01\x01"),
        # command #5 is go_to_lift_percentage (WindowCovering.ServerCommandDefs.go_to_lift_percentage.id)
        # expect a frame to set data point id 2 to a int value of 80 (100-20%)
        (
            "go_to_lift_percentage",
            0x05,
            [20],
            b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\x50",
        ),
    ),
)
async def test_zemismart_zm25r3_cover_commands(
    zigpy_device_from_v2_quirk, command_name, command_id, args, expected_frame
):
    """Test cluster move commands send the correct frames for Zemismart ZM25R3."""

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    cover_cluster = device.endpoints[1].window_covering

    assert len(tuya_listener.cluster_commands) == 0
    assert len(tuya_listener.attribute_updates) == 0
    assert cover_cluster.server_commands[command_id].name == command_name

    with mock.patch.object(
        tuya_cluster.endpoint,
        "request",
        return_value=foundation.Status.SUCCESS,
        autospec=True,
    ) as m1:
        # This is how HA calls the command (in zha/zigbee/device.py.) If we need to support kwargs
        # it needs to call convert_to_zcl_values as well.
        method = getattr(cover_cluster, command_name)
        rsp = await method(*(args or []))

        await wait_for_zigpy_tasks()
        # go_to_lift_percentage sends two requests (one per position DP), so we use assert_any_call
        # to check that at least one matches and ignore the sequence number.
        m1.assert_any_call(
            cluster=0xEF00,
            sequence=mock.ANY,
            data=AnyTSNTuyaFrame(expected_frame),
            command_id=0,
            timeout=mock.ANY,
            expect_reply=mock.ANY,
            use_ieee=mock.ANY,
            ask_for_ack=mock.ANY,
            priority=mock.ANY,
            retries=mock.ANY,
            retry_delay=mock.ANY,
        )
        assert rsp.status == foundation.Status.SUCCESS


@pytest.mark.parametrize(
    "name, value, expected_frame",
    (
        pytest.param(
            "motor_direction",
            MotorDirection.Back,
            b"\x01\x01\x00\x00\x01\x05\x04\x00\x01\x01",
            id="motor_direction",
        ),
    ),
)
async def test_zemismart_zm25r3_attributes_set(
    zigpy_device_from_v2_quirk, name, value, expected_frame
):
    """Test the expected frame is sent when setting attributes for Zemismart ZM25R3."""

    await _assert_zm25r3_attribute_set_sends_expected_frame(
        zigpy_device_from_v2_quirk, name, value, expected_frame
    )


@pytest.mark.parametrize(
    "attribute_name, attribute_value, expected_frame",
    (
        pytest.param(
            "border",
            BorderSetting.Up,
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x00",
            id="set_upper_limit",
        ),
        pytest.param(
            "border",
            BorderSetting.Down,
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x01",
            id="set_lower_limit",
        ),
        pytest.param(
            "border",
            BorderSetting.Up_delete,
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x02",
            id="delete_upper_limit",
        ),
        pytest.param(
            "border",
            BorderSetting.Down_delete,
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x03",
            id="delete_lower_limit",
        ),
        pytest.param(
            "border",
            BorderSetting.Remove_top_bottom,
            b"\x01\x01\x00\x00\x01\x10\x04\x00\x01\x04",
            id="delete_all_limits",
        ),
        pytest.param(
            "small_step",
            SmallStep.Open,
            b"\x01\x01\x00\x00\x01\x14\x04\x00\x01\x00",
            id="small_step_open",
        ),
        pytest.param(
            "small_step",
            SmallStep.Close,
            b"\x01\x01\x00\x00\x01\x14\x04\x00\x01\x01",
            id="small_step_close",
        ),
    ),
)
async def test_zemismart_zm25r3_attribute_based_commands(
    zigpy_device_from_v2_quirk, attribute_name, attribute_value, expected_frame
):
    """Test the limit and small step commands for Zemismart ZM25R3.

    These commands are exposed as 'border' and 'small_step' attributes of the zigbee device
    and entities in HA that write command id values to these attributes. They're not really
    attributes, but this is a convenient way to expose them in HA without needing to
    write a custom tuya cluster class. This tests that HA's write_attributes call sends
    the correct Tuya DP frame.
    """
    await _assert_zm25r3_attribute_set_sends_expected_frame(
        zigpy_device_from_v2_quirk, attribute_name, attribute_value, expected_frame
    )


async def _assert_zm25r3_attribute_set_sends_expected_frame(
    zigpy_device_from_v2_quirk, attribute_name, attribute_value, expected_frame
):
    """Assert that writing a tuya attribute sends the expected DP frame.

    Mimics HA pressing a write_attr_button entity and calling write_attributes
    on the tuya cluster.
    """
    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint,
        "request",
        return_value=foundation.Status.SUCCESS,
        autospec=True,
    ) as m1:
        write_results = await tuya_cluster.write_attributes(
            {attribute_name: attribute_value}
        )

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=0xEF00,
            sequence=1,
            data=expected_frame,
            command_id=0,
            timeout=mock.ANY,
            expect_reply=mock.ANY,
            use_ieee=mock.ANY,
            ask_for_ack=mock.ANY,
            priority=mock.ANY,
            retries=mock.ANY,
            retry_delay=mock.ANY,
        )
        assert write_results == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]


async def test_zemismart_zm25r3_unknown_command(zigpy_device_from_v2_quirk):
    """Test calling an unexpected cluster command returns an unsupported status."""

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
    "frame, cluster_name, attr_key, attr_value",
    (
        pytest.param(
            # TuyaDatapointData(dp=3, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x00\x00\x00\x14', *payload=20))
            b"\x09\x00\x02\x00\x00\x03\x02\x00\x04\x00\x00\x00\x14",
            "window_covering",
            # current_position_lift_percentage (blind reports % closed, cluster attribute expects % open)
            0x0008,
            80,
            id="position_report",
        ),
        pytest.param(
            # DP 5, motor_direction: backward
            b"\x09\x00\x02\x00\x00\x05\x02\x00\x04\x00\x00\x00\x01",
            "tuya_manufacturer",
            "motor_direction",
            MotorDirection.Back,
            id="motor_direction_backward",
        ),
        pytest.param(
            # TuyaDatapointData(dp=13, data=TuyaData(dp_type=<TuyaDPType.VALUE: 2>, function=0, raw=b'\x00\x00\x00\\', *payload=92))
            b"\x09\x00\x02\x00\x00\x0d\x02\x00\x04\x00\x00\x00\x5c",
            "power",
            # battery_percentage_remaining (attribute expects 2x real percentage)
            0x0021,
            184,
            id="battery_percentage_remaining",
        ),
    ),
)
async def test_zemismart_zm25r3_report_values(
    zigpy_device_from_v2_quirk, frame, cluster_name, attr_key, attr_value
):
    """Test receiving simple frames from a Zemismart ZM25R3 updates the expected attributes."""

    cover_dev = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = cover_dev.endpoints[1].tuya_manufacturer
    target_cluster = getattr(cover_dev.endpoints[1], cluster_name)
    target_listener = ClusterListener(target_cluster)

    assert len(target_listener.cluster_commands) == 0
    assert len(target_listener.attribute_updates) == 0

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)
    attr_id = (
        target_cluster.attributes_by_name[attr_key].id
        if isinstance(attr_key, str)
        else attr_key
    )
    assert target_listener.attribute_updates == [(attr_id, attr_value)]


async def test_zemismart_zm25r3_report_multiple_values(zigpy_device_from_v2_quirk):
    """Test receiving a complex frame from a Zemismart ZM25R3 updates all 3 expected attributes."""

    device = zigpy_device_from_v2_quirk("_TZE200_eevqq1uv", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    cover_cluster = device.endpoints[1].window_covering
    cover_listener = ClusterListener(cover_cluster)
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    # A real packet with multiple Tuya data points 1,7,3,5 & 13 (motor status, unknown, position,
    # direction, battery)
    frame = b"\x09\x00\x02\x00\x00\x01\x04\x00\x01\x01\x07\x04\x00\x01\x01\x03\x02\x00\x04\x00\x00\x00\x14\x05\x04\x00\x01\x01\x0d\x02\x00\x04\x00\x00\x00\x5c"
    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    # Ignore DP 1 & 7.
    # DP 1 should be interpreted as a motor status when received (e.g. opening, stopped, closing),
    # but the existing quirk builder infrastructure maps DPs to the same attribute for both reading
    # and writing, so it ends up being interpreted as a tuya_cover_command attribute update, which
    # doesn't seem that useful to test. It would be more logical to map it to a separate, read only
    # 'motor_status' attribute but it's not really noticeable to HA users so just ignore it.
    # DP 7 is in the packet but I don't know what it's for, ignore it too.

    # DP 3 is position
    assert (
        cover_cluster.attributes_by_name["current_position_lift_percentage"].id,
        80,  # device reports % closed, cluster attribute expects % open
    ) in cover_listener.attribute_updates
    # DP 5 is direction
    assert (
        tuya_cluster.attributes_by_name["motor_direction"].id,
        MotorDirection.Back,
    ) in tuya_listener.attribute_updates
    # DP 13 is battery percentage
    assert (
        power_cluster.attributes_by_name["battery_percentage_remaining"].id,
        92 * 2,  # (attribute expects 2x real percentage)
    ) in power_listener.attribute_updates
