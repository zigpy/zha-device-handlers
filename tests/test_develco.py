"""Tests for Develco/Frient."""

from unittest import mock

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasAce, IasWd, IasZone
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.develco.intelligent_keypad import MANUFACTURER_CODE

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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    ias_ace._remember_panel_state(
        IasAce.PanelStatus.Panel_Disarmed,
        0,
        IasAce.AudibleNotification.Mute,
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
        IasAce.AudibleNotification.Mute,
        IasAce.AlarmStatus.No_Alarm,
    )


async def test_frient_keypad_panel_status_normal(zigpy_device_from_v2_quirk):
    """Test panel status updates pass through when not suppressed."""
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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]

    with mock.patch.object(IasAce, "client_command", new=mock.AsyncMock()) as send:
        await ias_ace.panel_status_changed(
            IasAce.PanelStatus.Armed_Away,
            15,
            IasAce.AudibleNotification.Default_Sound,
            IasAce.AlarmStatus.No_Alarm,
        )

    send.assert_called_once_with(
        ias_ace.ClientCommandDefs.panel_status_changed.id,
        IasAce.PanelStatus.Armed_Away,
        15,
        IasAce.AudibleNotification.Default_Sound,
        IasAce.AlarmStatus.No_Alarm,
    )
    assert ias_ace._cached_panel_status == IasAce.PanelStatus.Armed_Away


async def test_frient_keypad_panel_status_response_cached(zigpy_device_from_v2_quirk):
    """Test panel status response reuses cached values when available."""
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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    ias_ace._remember_panel_state(
        IasAce.PanelStatus.Panel_Disarmed,
        0,
        IasAce.AudibleNotification.Mute,
        IasAce.AlarmStatus.No_Alarm,
    )

    with mock.patch.object(IasAce, "client_command", new=mock.AsyncMock()) as send:
        await ias_ace.panel_status_response(
            IasAce.PanelStatus.Armed_Night,
            30,
            IasAce.AudibleNotification.Default_Sound,
            IasAce.AlarmStatus.Fire,
        )

    send.assert_called_once_with(
        ias_ace.ClientCommandDefs.panel_status_response.id,
        IasAce.PanelStatus.Panel_Disarmed,
        0,
        IasAce.AudibleNotification.Mute,
        IasAce.AlarmStatus.No_Alarm,
    )


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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]

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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    attrs = {
        ias_ace.AttributeDefs.auto_arm_mode.id: (
            ias_ace.AutoArmMode.Auto_Arm_in_Away_Mode
        ),
        ias_ace.AttributeDefs.auto_disarm.id: True,
        ias_ace.AttributeDefs.auto_arm_disarm.id: (
            ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Pin
        ),
        ias_ace.AttributeDefs.pin_length.id: 6,
    }

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes(attrs, timeout=5)

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
    assert call_args.kwargs["timeout"] == 5

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
    assert attrs == {
        ias_ace.AttributeDefs.auto_arm_mode.id: (
            ias_ace.AutoArmMode.Auto_Arm_in_Away_Mode
        ),
        ias_ace.AttributeDefs.auto_disarm.id: True,
        ias_ace.AttributeDefs.auto_arm_disarm.id: (
            ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Pin
        ),
        ias_ace.AttributeDefs.pin_length.id: 6,
    }


async def test_frient_keypad_write_attributes_names(zigpy_device_from_v2_quirk):
    """Test keypad attributes are accepted by name and written with manufacturer code."""
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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes(
            {
                ias_ace.AttributeDefs.auto_arm_mode.name: (
                    ias_ace.AutoArmMode.Auto_Arm_in_Night_Mode
                ),
                ias_ace.AttributeDefs.auto_arm_disarm.name: (
                    ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Rfid
                ),
                ias_ace.AttributeDefs.pin_length.name: 5,
            }
        )

    assert write_mock.call_count == 1
    assert write_mock.call_args.kwargs["manufacturer"] == MANUFACTURER_CODE

    assert (
        ias_ace.get(ias_ace.AttributeDefs.auto_arm_mode.id)
        == ias_ace.AutoArmMode.Auto_Arm_in_Night_Mode
    )
    assert (
        ias_ace.get(ias_ace.AttributeDefs.auto_arm_disarm.id)
        == ias_ace.AutoArmDisarm.Auto_Arm_Disarm_Using_Rfid
    )
    assert ias_ace.get(ias_ace.AttributeDefs.pin_length.id) == 5


async def test_frient_keypad_write_attributes_explicit_manufacturer(
    zigpy_device_from_v2_quirk,
):
    """Test an explicit manufacturer kwarg is preserved without duplication."""
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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes(
            {
                ias_ace.AttributeDefs.auto_disarm.name: True,
            },
            manufacturer=MANUFACTURER_CODE,
            timeout=5,
        )

    assert write_mock.call_count == 1
    assert write_mock.call_args.args[0] == {
        ias_ace.AttributeDefs.auto_disarm.name: True,
    }
    assert write_mock.call_args.kwargs["manufacturer"] == MANUFACTURER_CODE
    assert write_mock.call_args.kwargs["timeout"] == 5


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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes(
            {
                ias_ace.AttributeDefs.auto_disarm.name: False,
                0xFFFD: 2,
            },
            priority=1,
        )

    assert write_mock.call_count == 2
    first_call = write_mock.call_args_list[0]
    second_call = write_mock.call_args_list[1]

    assert first_call.args[0] == {ias_ace.AttributeDefs.auto_disarm.name: False}
    assert first_call.kwargs["manufacturer"] == MANUFACTURER_CODE
    assert first_call.kwargs["priority"] == 1
    assert second_call.args[0] == {0xFFFD: 2}
    assert "manufacturer" not in second_call.kwargs
    assert second_call.kwargs["priority"] == 1


async def test_frient_keypad_write_attributes_standard_only(zigpy_device_from_v2_quirk):
    """Test non-keypad attributes pass through without manufacturer code."""
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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]
    write_status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[write_status]),
    ) as write_mock:
        await ias_ace.write_attributes({0xFFFD: 1})

    assert write_mock.call_count == 1
    assert write_mock.call_args.args[0] == {0xFFFD: 1}
    assert "manufacturer" not in write_mock.call_args.kwargs


async def test_frient_keypad_write_attributes_empty(zigpy_device_from_v2_quirk):
    """Test empty writes short-circuit with success status."""
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

    ias_ace = device.endpoints[44].out_clusters[IasAce.cluster_id]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(),
    ) as write_mock:
        result = await ias_ace.write_attributes({})

    assert write_mock.call_count == 0
    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]


