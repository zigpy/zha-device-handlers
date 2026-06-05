"""Test units for Tuya covers."""

from unittest import mock

from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaWindowCovering
from zhaquirks.tuya.ts0601_cover import TuyaMoesCover0601

zhaquirks.setup()


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
    assert isinstance(quirked, CustomDeviceV2)

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
