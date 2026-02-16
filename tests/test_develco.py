"""Tests for Develco/Frient."""

from unittest import mock

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks

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
    """Test Frient EMI Norwegian HAN metering attribute reports."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-132",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )

    metering_cluster = device.endpoints[2].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)

    # send mfr-specific attribute report with divisor attribute ID — should be ignored
    # Frame: 0x1c (mfr-specific, server-to-client, disable-default-rsp),
    #        TSN=3, cmd=0x0a (Report_Attributes), attr=0x0302 (divisor), value=512
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Metering.cluster_id,
            src_ep=2,
            dst_ep=1,
            data=t.SerializableBytes(b"\x1c\x15\x10\x03\x0a\x02\x03\x31\x00\x02"),
        )
    )

    # TODO: mfr-specific report should not update the standard divisor attribute,
    #  but zigpy currently does not filter this. Fix in zigpy.
    assert len(metering_listener.attribute_updates) == 0
    assert metering_cluster.get(Metering.AttributeDefs.divisor) is None

    # send real attribute report with current_summ_delivered, current_summ_received,
    # instantaneous_demand, and status
    # Frame: 0x18 (server-to-client, disable-default-rsp),
    #        TSN=54, cmd=0x0a (Report_Attributes)
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Metering.cluster_id,
            src_ep=2,
            dst_ep=1,
            data=t.SerializableBytes(
                b"\x18\x36\x0a\x00\x00\x25\x08\xcc\xd4\x01\x00\x00"
                b"\x01\x00\x25\x00\x00\x00\x00\x00\x00"
                b"\x00\x04\x2a\xa1\x0f\x00"
                b"\x00\x02\x18\x00"
            ),
        )
    )

    # attribute_updated events should be emitted (5 instead of 4 due to zigpy bug above)
    assert len(metering_listener.attribute_updates) == 5
    assert (
        metering_cluster.get(Metering.AttributeDefs.current_summ_delivered.id)
        == 30_723_080
    )
    assert metering_cluster.get(Metering.AttributeDefs.current_summ_received.id) == 0
    assert metering_cluster.get(Metering.AttributeDefs.instantaneous_demand.id) == 4001
    assert metering_cluster.get(Metering.AttributeDefs.status.id) == 0
