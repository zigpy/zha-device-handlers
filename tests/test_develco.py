"""Tests for Develco/Frient."""

from datetime import UTC, datetime
from unittest import mock

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasAce, IasWd, IasZone
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.develco.intelligent_keypad import (
    MANUFACTURER_CODE,
    parse_emergency_timestamp,
)

zhaquirks.setup()


async def test_frient_emi(zigpy_device_from_v2_quirk):
    """Test that the EMI correctly forwards custom attributes."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )

    metering_cluster = device.endpoints[2].smartenergy_metering
    manufacturer_cluster = device.endpoints[2].in_clusters[0xFD10]
    pulse_config_attr_id = manufacturer_cluster.AttributeDefs.pulse_configuration.id

    request_patch = mock.patch("zigpy.device.Device.request", mock.AsyncMock())
    with request_patch as request_mock:
        # this is not the correct answer for write/read attributes, so they fail,
        # but we only care about the request to the device here
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        # the device uses manufacturer code 4117, but tests fake it as 1234,
        # as it is normally read from the node description

        # read custom attribute
        await manufacturer_cluster.read_attributes([pulse_config_attr_id])

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert request_mock.call_args[1]["data"] == b"\x04\xd2\x04\x01\x00\x00\x03"

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 1
        assert zcl_header.manufacturer == 1234  # manufacturer id used by mock device
        assert zcl_header.command_id == foundation.GeneralCommand.Read_Attributes
        assert attr_data == b"\x00\x03"

        request_mock.reset_mock()

        # write custom attribute
        await manufacturer_cluster.write_attributes({pulse_config_attr_id: "42"})

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert (
            request_mock.call_args[1]["data"] == b"\x04\xd2\x04\x02\x02\x00\x03!*\x00"
        )

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 1
        assert zcl_header.manufacturer == 1234  # manufacturer id used by mock device
        assert zcl_header.command_id == foundation.GeneralCommand.Write_Attributes
        assert attr_data == b"\x00\x03!*\x00"

        request_mock.reset_mock()

        # read non-custom attribute
        await metering_cluster.read_attributes(
            [metering_cluster.AttributeDefs.current_summ_delivered.id]
        )

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert request_mock.call_args[1]["data"] == b"\x00\x03\x00\x00\x00"

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 0
        assert zcl_header.manufacturer is None
        assert zcl_header.command_id == foundation.GeneralCommand.Read_Attributes
        assert attr_data == b"\x00\x00"

        request_mock.reset_mock()

        # write non-custom attribute
        await metering_cluster.write_attributes(
            {metering_cluster.AttributeDefs.current_summ_delivered.id: 100}
        )

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert (
            request_mock.call_args[1]["data"]
            == b"\x00\x04\x02\x00\x00%d\x00\x00\x00\x00\x00"
        )

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 0
        assert zcl_header.manufacturer is None
        assert zcl_header.command_id == foundation.GeneralCommand.Write_Attributes
        assert attr_data == b"\x00\x00%d\x00\x00\x00\x00\x00"


async def test_mfg_cluster_events(zigpy_device_from_v2_quirk):
    """Test Frient EMI Norwegian HAN ignoring incorrect divisor attribute reports."""
    device = zigpy_device_from_v2_quirk("frient A/S", "EMIZB-132", endpoint_ids=[1, 2])

    metering_cluster = device.endpoints[2].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)

    # divisor already fixed at 1000
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == 1000

    # send incorrect divisor attribute report
    # Frame: 0x18 (non-mfr-specific, server-to-client, disable-default-rsp),
    #        TSN=1, cmd=0x0a (Report_Attributes), attr=0x0302 (divisor), value=512
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            data=t.SerializableBytes(b"\x18\x01\x0a\x02\x03\x22\x00\x02\x00"),
        )
    )

    # attribute_updated event should not be emitted
    assert len(metering_listener.attribute_updates) == 0

    # divisor should still be fixed at 1000
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == 1000

    # send current_summ_delivered attribute report
    # Frame: 0x18, TSN=1, cmd=0x0a, attr=0x0000, value=1234 (uint48)
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            data=t.SerializableBytes(
                b"\x18\x01\x0a\x00\x00\x25\xd2\x04\x00\x00\x00\x00"
            ),
        )
    )

    # attribute_updated event should be emitted
    assert len(metering_listener.attribute_updates) == 1
    assert (
        metering_cluster.get(Metering.AttributeDefs.current_summ_delivered.id) == 1234
    )


async def test_frient_keypad_emergency_updates(zigpy_device_from_v2_quirk):
    """Test SOS button handling updates emergency attributes."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    emergency_cluster = device.endpoints[44].frient_emergency

    hdr = foundation.ZCLHeader(
        frame_control=foundation.FrameControl(
            frame_type=foundation.FrameType.CLUSTER_COMMAND,
            is_manufacturer_specific=False,
            direction=foundation.Direction.Client_to_Server,
            disable_default_response=False,
            reserved=0,
        ),
        tsn=1,
        command_id=IasAce.ServerCommandDefs.emergency.id,
    )

    send_patch = mock.patch.object(ias_ace, "send_default_rsp")
    with send_patch as send_default_rsp:
        ias_ace.handle_cluster_request(hdr, [])

    assert emergency_cluster.get(emergency_cluster.AttributeDefs.emergency.id)
    assert emergency_cluster.get(
        emergency_cluster.AttributeDefs.last_emergency_triggered.id
    )
    assert ias_ace._emergency_reset_handle is not None
    send_default_rsp.assert_called_once()


async def test_frient_keypad_last_code_updates(zigpy_device_from_v2_quirk):
    """Test arm command stores the last keypad code."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    last_code_cluster = device.endpoints[44].frient_last_code

    hdr = foundation.ZCLHeader(
        frame_control=foundation.FrameControl(
            frame_type=foundation.FrameType.CLUSTER_COMMAND,
            is_manufacturer_specific=False,
            direction=foundation.Direction.Client_to_Server,
            disable_default_response=True,
            reserved=0,
        ),
        tsn=2,
        command_id=IasAce.ServerCommandDefs.arm.id,
    )

    ias_ace.handle_cluster_request(
        hdr,
        [IasAce.ArmMode.Arm_All_Zones, b"1234"],
    )

    assert last_code_cluster.get(last_code_cluster.AttributeDefs.last_code.id) == "1234"


async def test_frient_keypad_panel_status_suppression(zigpy_device_from_v2_quirk):
    """Test panel status responses keep cached values when suppression is active."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    ias_ace._remember_panel_state(
        IasAce.PanelStatus.Panel_Disarmed,
        0,
        IasAce.AudibleNotification.Default_Sound,
        IasAce.AlarmStatus.No_Alarm,
    )
    ias_ace._suppress_panel_updates = True

    with mock.patch.object(IasAce, "client_command", new=mock.AsyncMock()) as send:
        await ias_ace.panel_status_changed(
            IasAce.PanelStatus.Armed_Away,
            10,
            IasAce.AudibleNotification.Default_Sound,
            IasAce.AlarmStatus.No_Alarm,
        )

    send.assert_called_once_with(
        ias_ace.ClientCommandDefs.panel_status_changed.id,
        IasAce.PanelStatus.Panel_Disarmed,
        0,
        IasAce.AudibleNotification.Default_Sound,
        IasAce.AlarmStatus.No_Alarm,
    )


async def test_frient_keypad_emergency_resets(zigpy_device_from_v2_quirk):
    """Test emergency reset clears the emergency flag."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    emergency_cluster = device.endpoints[44].frient_emergency

    hdr = foundation.ZCLHeader(
        frame_control=foundation.FrameControl(
            frame_type=foundation.FrameType.CLUSTER_COMMAND,
            is_manufacturer_specific=False,
            direction=foundation.Direction.Client_to_Server,
            disable_default_response=True,
            reserved=0,
        ),
        tsn=3,
        command_id=IasAce.ServerCommandDefs.emergency.id,
    )

    ias_ace.handle_cluster_request(hdr, [])
    assert emergency_cluster.get(emergency_cluster.AttributeDefs.emergency.id)

    ias_ace._reset_emergency_flag()
    assert not emergency_cluster.get(emergency_cluster.AttributeDefs.emergency.id)


async def test_frient_keypad_arm_response_suppression(zigpy_device_from_v2_quirk):
    """Test arm response toggles suppression flag."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace

    with mock.patch.object(IasAce, "client_command", new=mock.AsyncMock()):
        await ias_ace.arm_response(IasAce.ArmNotification.Invalid_Arm_Disarm_Code)
        assert ias_ace._suppress_panel_updates is True

        await ias_ace.arm_response(IasAce.ArmNotification.All_Zones_Armed)
        assert ias_ace._suppress_panel_updates is False


async def test_frient_keypad_write_attributes_manufacturer(zigpy_device_from_v2_quirk):
    """Test keypad attributes are written with the manufacturer code."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes(
            {
                ias_ace.AttributeDefs.auto_arm_mode.id: (
                    ias_ace.AutoArmMode.Auto_Arm_in_Away_Mode
                ),
                ias_ace.AttributeDefs.auto_disarm.id: True,
                ias_ace.AttributeDefs.auto_arm_disarm.id: (
                    ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Pin
                ),
                ias_ace.AttributeDefs.pin_length.id: 6,
            }
        )

    assert write_mock.call_count == 1
    call_args = write_mock.call_args
    assert call_args.args[0] == {
        ias_ace.AttributeDefs.auto_arm_mode.name: (
            ias_ace.AutoArmMode.Auto_Arm_in_Away_Mode
        ),
        ias_ace.AttributeDefs.auto_disarm.name: True,
        ias_ace.AttributeDefs.auto_arm_disarm.name: (
            ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Pin
        ),
        ias_ace.AttributeDefs.pin_length.name: 6,
    }
    assert call_args.kwargs["manufacturer"] == MANUFACTURER_CODE

    assert (
        ias_ace.get(ias_ace.AttributeDefs.auto_arm_mode.id)
        == ias_ace.AutoArmMode.Auto_Arm_in_Away_Mode
    )
    assert ias_ace.get(ias_ace.AttributeDefs.auto_disarm.id) is True
    assert (
        ias_ace.get(ias_ace.AttributeDefs.auto_arm_disarm.id)
        == ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Pin
    )
    assert ias_ace.get(ias_ace.AttributeDefs.pin_length.id) == 6


async def test_frient_keypad_write_attributes_mixed(zigpy_device_from_v2_quirk):
    """Test mixed keypad writes split manufacturer and standard attributes."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes(
            {
                ias_ace.AttributeDefs.auto_disarm.name: False,
                0xFFFD: 2,
            }
        )

    assert write_mock.call_count == 2
    first_call = write_mock.call_args_list[0]
    second_call = write_mock.call_args_list[1]

    assert first_call.args[0] == {ias_ace.AttributeDefs.auto_disarm.name: False}
    assert first_call.kwargs["manufacturer"] == MANUFACTURER_CODE
    assert second_call.args[0] == {0xFFFD: 2}
    assert "manufacturer" not in second_call.kwargs


def test_parse_emergency_timestamp_variants():
    """Test emergency timestamp parsing handles empty, valid, and invalid values."""
    assert parse_emergency_timestamp(None) is None
    assert parse_emergency_timestamp("") is None

    naive = datetime(2024, 1, 1, 12, 0, 0)
    parsed = parse_emergency_timestamp(naive)
    assert parsed is not None
    assert parsed.tzinfo is not None

    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert parse_emergency_timestamp(aware) == aware

    iso_value = "2024-02-03T04:05:06+00:00"
    parsed_iso = parse_emergency_timestamp(iso_value)
    assert parsed_iso is not None
    assert parsed_iso.isoformat() == iso_value

    assert parse_emergency_timestamp("not-a-date") is None


async def test_frient_keypad_store_last_code_variants(zigpy_device_from_v2_quirk):
    """Test keypad stores last code from multiple argument formats."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    last_code_cluster = device.endpoints[44].frient_last_code

    ias_ace._store_last_code({"arm_disarm_code": "2468"})
    assert last_code_cluster.get(last_code_cluster.AttributeDefs.last_code.id) == "2468"

    class CodePayload:
        arm_disarm_code = b"1357"

    ias_ace._store_last_code(CodePayload())
    assert last_code_cluster.get(last_code_cluster.AttributeDefs.last_code.id) == "1357"

    ias_ace._store_last_code([])
    assert last_code_cluster.get(last_code_cluster.AttributeDefs.last_code.id) == "1357"


async def test_frient_keypad_emergency_reschedule(zigpy_device_from_v2_quirk):
    """Test emergency trigger cancels existing timer and schedules a new one."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "KEPZB-112",
        endpoint_ids=[1, 44],
        cluster_ids={
            44: {
                IasAce.cluster_id: ClusterType.Client,
                IasZone.cluster_id: ClusterType.Server,
                IasWd.cluster_id: ClusterType.Server,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )

    ias_ace = device.endpoints[44].ias_ace
    emergency_cluster = device.endpoints[44].frient_emergency

    old_handle = mock.Mock()
    ias_ace._emergency_reset_handle = old_handle
    loop = mock.Mock()
    new_handle = mock.Mock()
    loop.call_later.return_value = new_handle

    with (
        mock.patch("asyncio.get_running_loop", side_effect=RuntimeError),
        mock.patch("asyncio.get_event_loop", return_value=loop),
    ):
        ias_ace._track_emergency_trigger()

    old_handle.cancel.assert_called_once()
    loop.call_later.assert_called_once()
    assert ias_ace._emergency_reset_handle == new_handle
    assert emergency_cluster.get(emergency_cluster.AttributeDefs.emergency.id) is True
