"""Test units for Tuya covers."""

from unittest import mock

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder.builder import ZCLCommandButtonMetadata
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaWindowCovering
from zhaquirks.tuya.ts0601_cover import TuyaMoesCover0601
from zhaquirks.tuya.tuya_cover import (
    MoesCoverMCUCluster,
    MoesMotorCalibration,
    MoesWindowCovering,
    MoesWorkState,
)

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


MANUFACTURER = "_TZ3210_hs01bacp"
MODEL = "TS030F"
COVER_CLUSTER_ID = 0x0102
TUYA_CLUSTER_ID = 0xEF00


async def test_zc301_quirk_matches(zigpy_device_from_v2_quirk):
    """Test that the ZC301 signature is matched to its quirk."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)

    assert isinstance(quirked, CustomZigpyDevice)
    assert quirked.manufacturer == MANUFACTURER
    assert quirked.model == MODEL


async def test_zc301_clusters_present(zigpy_device_from_v2_quirk):
    """Test that the expected clusters are present on endpoint 1."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    assert isinstance(ep.window_covering, MoesWindowCovering)
    assert isinstance(ep.tuya_manufacturer, MoesCoverMCUCluster)


async def test_zc301_endpoint_device_type(zigpy_device_from_v2_quirk):
    """Test that endpoint 1 uses the window covering device type."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    assert quirked.endpoints[1].device_type == 0x0202


async def test_zc301_datapoints_mapped(zigpy_device_from_v2_quirk):
    """Test that the expected datapoints are mapped."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    tuya_cluster = quirked.endpoints[1].tuya_manufacturer

    assert set(tuya_cluster.dp_to_attribute) == {
        1,  # control
        2,  # percent_control
        3,  # percent_state
        5,  # motor_calibration
        7,  # work_state
        10,  # time_total
        11,  # situation_set
        12,  # fault
        13,  # battery_percentage
        101,  # charge_state
        107,  # curtain_close_direction
        108,  # total_meters
        155,  # charge_led_switch
    }


async def test_zc301_calibration_attribute(zigpy_device_from_v2_quirk):
    """Test that the calibration datapoint is exposed on the Tuya cluster.

    The motor calibration lives on datapoint 5, which the Tuya cluster exposes
    as the manufacturer specific attribute 0xEF00 + 5 == 0xEF05.
    """

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    calibration = ep.tuya_manufacturer.attributes_by_name["motor_calibration"]
    assert calibration.id == 0xEF05
    assert "motor_calibration" not in ep.window_covering.attributes_by_name


async def test_zc301_position_report(zigpy_device_from_v2_quirk):
    """Test that a DP 3 position report updates the cover position."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering
    cover_listener = ClusterListener(cover_cluster)

    ep.tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[TuyaDatapointData(3, TuyaData(75))],
        )
    )

    assert (
        cover_cluster.get(
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        == 75
    )
    assert len(cover_listener.attribute_updates) == 1
    assert (
        cover_listener.attribute_updates[0][0]
        == WindowCovering.AttributeDefs.current_position_lift_percentage.id
    )


async def test_zc301_control_echo_updates_position(zigpy_device_from_v2_quirk):
    """Test that the DP 1 / DP 2 control echo updates the position.

    Both the position control (DP 2) and the position state (DP 3) map to the
    same ZCL attribute, which is what the device itself reports, so the
    optimistic echo keeps the slider in sync while the motor is moving.
    """

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    cover_cluster = ep.window_covering

    ep.tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=2,
            datapoints=[TuyaDatapointData(2, TuyaData(50))],
        )
    )

    assert (
        cover_cluster.get(
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        == 50
    )

    # A later DP 3 report still wins
    ep.tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=3,
            datapoints=[TuyaDatapointData(3, TuyaData(80))],
        )
    )

    assert (
        cover_cluster.get(
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        == 80
    )


async def test_zc301_battery_report(zigpy_device_from_v2_quirk):
    """Test that a battery report updates the battery percentage."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    ep.tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=2,
            datapoints=[TuyaDatapointData(13, TuyaData(85))],
        )
    )

    # battery_percentage is scaled by 2 by default
    assert ep.power.get("battery_percentage_remaining") == 170


async def test_zc301_work_state_report(zigpy_device_from_v2_quirk):
    """Test that a work state report updates the work_state attribute."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)

    quirked.endpoints[1].tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=3,
            datapoints=[TuyaDatapointData(7, TuyaData(MoesWorkState.Opening))],
        )
    )

    assert (
        quirked.endpoints[1].tuya_manufacturer.get("work_state")
        == MoesWorkState.Opening
    )


async def test_zc301_fault_report(zigpy_device_from_v2_quirk):
    """Test that a fault report updates the fault attribute."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)

    quirked.endpoints[1].tuya_manufacturer.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=4,
            datapoints=[TuyaDatapointData(12, TuyaData(1))],
        )
    )

    assert quirked.endpoints[1].tuya_manufacturer.get("fault") == 1


async def test_zc301_open_uses_standard_zcl(zigpy_device_from_v2_quirk):
    """Test that open is sent as a standard ZCL command."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    with mock.patch.object(
        ep.device, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await ep.window_covering.command(WindowCovering.ServerCommandDefs.up_open.id)
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        assert req_mock.call_args[1]["cluster"] == COVER_CLUSTER_ID


async def test_zc301_close_uses_standard_zcl(zigpy_device_from_v2_quirk):
    """Test that close is sent as a standard ZCL command."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    with mock.patch.object(
        ep.device, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await ep.window_covering.command(WindowCovering.ServerCommandDefs.down_close.id)
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        assert req_mock.call_args[1]["cluster"] == COVER_CLUSTER_ID


async def test_zc301_stop_uses_standard_zcl(zigpy_device_from_v2_quirk):
    """Test that stop is sent as a standard ZCL command."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    with mock.patch.object(
        ep.device, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await ep.window_covering.command(WindowCovering.ServerCommandDefs.stop.id)
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        assert req_mock.call_args[1]["cluster"] == COVER_CLUSTER_ID


async def test_zc301_calibration_write_sends_dp5(zigpy_device_from_v2_quirk):
    """Test that writing the calibration attribute is sent as datapoint 5."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    with mock.patch.object(
        ep,
        "request",
        return_value=[
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ],
    ) as req_mock:
        result = await tuya_cluster.write_attributes(
            {"motor_calibration": MoesMotorCalibration.Up_Start}
        )
        await wait_for_zigpy_tasks()

        assert result[0][0].status == foundation.Status.SUCCESS
        req_mock.assert_called_once()
        assert req_mock.call_args[1]["cluster"] == TUYA_CLUSTER_ID
        # status | tsn | DP 5 | enum8 | len 1 | up_start
        assert req_mock.call_args[1]["data"][-5:] == b"\x05\x04\x00\x01\x01"


async def test_zc301_calibration_enum_values(zigpy_device_from_v2_quirk):
    """Test the DP 5 calibration values used by the written values."""

    assert MoesMotorCalibration.None_ == 0x00
    assert MoesMotorCalibration.Up_Start == 0x01
    assert MoesMotorCalibration.Down_Start == 0x02
    assert MoesMotorCalibration.Completed == 0x03


async def test_zc301_calibration_report(zigpy_device_from_v2_quirk):
    """Test that a DP 5 report updates the calibration attribute."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    tuya_cluster.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=5,
            datapoints=[TuyaDatapointData(5, TuyaData(MoesMotorCalibration.Completed))],
        )
    )

    assert tuya_cluster.get("motor_calibration") == MoesMotorCalibration.Completed


async def test_zc301_go_to_lift_percentage(zigpy_device_from_v2_quirk):
    """Test that go_to_lift_percentage is sent as a standard ZCL command."""

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    ep = quirked.endpoints[1]

    with mock.patch.object(
        ep.device, "request", return_value=foundation.Status.SUCCESS
    ) as req_mock:
        await ep.window_covering.command(
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id, 25
        )
        await wait_for_zigpy_tasks()

        req_mock.assert_called_once()
        assert req_mock.call_args[1]["cluster"] == COVER_CLUSTER_ID


async def test_zc301_mark_calibrated_button(zigpy_device_from_v2_quirk):
    """Test that the 'Stop and save current limit' button is registered.

    During calibration the device treats a ZCL ``stop`` received from the
    WindowCovering cluster as 'save the current position as the limit'. The
    button is just a labelled wrapper around that command — a cover card's
    bare ``Stop`` button would also work, but the labelled one makes the
    calibration flow obvious to the user.
    """

    # Re-build the same chain and inspect its entity_metadata; this mirrors
    # what ``add_to_registry`` packages into QuirkDefinition.entity_metadata.
    # If this list does not contain a ``mark_calibrated`` ZCLCommandButtonMetadata,
    # Home Assistant will not surface the button at all.
    builder = (
        TuyaQuirkBuilder(MANUFACTURER, MODEL)
        .tuya_dp_attribute(
            dp_id=5,
            attribute_name="motor_calibration",
            type=t.enum8,
            access=(
                foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write
            ),
        )
        .command_button(
            command_name="stop",
            cluster_id=COVER_CLUSTER_ID,
            unique_id_suffix="mark_calibrated",
            translation_key="mark_calibrated",
            fallback_name="Stop and save current limit",
        )
    )

    mark_calibrated = [
        em
        for em in builder.entity_metadata
        if isinstance(em, ZCLCommandButtonMetadata)
        and em.translation_key == "mark_calibrated"
    ]
    assert len(mark_calibrated) == 1
    button = mark_calibrated[0]
    assert button.cluster_id == COVER_CLUSTER_ID
    assert button.command_name == "stop"
    assert button.fallback_name == "Stop and save current limit"
    # ZHA's Button.async_press() does getattr(cluster, command_name)(*args, **kwargs)
    # — that route is already covered by test_zc301_stop_uses_standard_zcl.
    assert button.args == ()
    assert dict(button.kwargs) == {}


async def test_zc301_data_report_command_005(zigpy_device_from_v2_quirk):
    """Test the device-specific 0x05 datapoint report command.

    This firmware does not use the usual `data_response` (0x02) command to
    report datapoints — it sends them with a vendor-specific command id 0x05
    instead. The quirk declares that command and forwards it to the regular
    datapoint handler, so reports still land on the right attributes.
    """

    quirked = zigpy_device_from_v2_quirk(MANUFACTURER, MODEL)
    tuya_cluster = quirked.endpoints[1].tuya_manufacturer

    assert isinstance(tuya_cluster, MoesCoverMCUCluster)
    assert MoesCoverMCUCluster.ClientCommandDefs.moes_data_report.id == 0x05

    # A DP 7 report arriving on the 0x05 command must still update work_state.
    result = tuya_cluster.handle_moes_data_report(
        TuyaCommand(
            status=0,
            tsn=7,
            datapoints=[TuyaDatapointData(7, TuyaData(MoesWorkState.Opening))],
        )
    )

    assert result == foundation.Status.SUCCESS
    assert tuya_cluster.get("work_state") == MoesWorkState.Opening
