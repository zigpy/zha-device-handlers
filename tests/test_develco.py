"""Tests for Develco/Frient."""

from unittest import mock

from zha.quirks import DEVICE_REGISTRY as ZHA_DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks

zhaquirks.setup()


async def test_frient_emi_v2_metadata_current_summation(zigpy_device_from_v2_quirk):
    """Test EMIZB-141 exposes current summation and reset button metadata."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )
    entry = ZHA_DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    entity_map = {
        m.translation_key: m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
        if m.translation_key is not None
    }

    assert (
        entity_map["current_summation"].fallback_name == "Current summation delivered"
    )
    assert (
        entity_map["reset_summation_delivered"].fallback_name
        == "Reset summation delivered"
    )


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
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id

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
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id

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
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id

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
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id

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


async def test_frient_emi_current_summation_write_request(zigpy_device_from_v2_quirk):
    """Test EMIZB-141 forwards current summation write as a mfg-specific write."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )

    manufacturer_cluster = device.endpoints[2].in_clusters[0xFD10]
    current_summation_attr_id = manufacturer_cluster.AttributeDefs.current_summation.id

    request_patch = mock.patch("zigpy.device.Device.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await manufacturer_cluster.write_attributes({current_summation_attr_id: 42})

        assert request_mock.call_count == 1
        assert request_mock.call_args.kwargs["cluster"] == Metering.cluster_id

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args.kwargs["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 1
        assert zcl_header.manufacturer == 1234
        assert zcl_header.command_id == foundation.GeneralCommand.Write_Attributes
        assert attr_data == b"\x01\x03%*\x00\x00\x00\x00\x00"


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


async def test_current_summation_cache_updated_on_successful_write(
    zigpy_device_from_v2_quirk,
):
    """Test that a successful write to current_summation caches the value locally."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )
    manufacturer_cluster = device.endpoints[2].in_clusters[0xFD10]
    attr_id = manufacturer_cluster.AttributeDefs.current_summation.id

    with mock.patch.object(
        manufacturer_cluster,
        "_write_attributes",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
                [],
            ]
        ),
    ):
        await manufacturer_cluster.write_attributes({"current_summation": 12345})
        assert manufacturer_cluster._attr_cache[attr_id] == 12345


async def test_current_summation_cache_not_updated_on_failed_write(
    zigpy_device_from_v2_quirk,
):
    """Test that a failed write to current_summation does not update the cache."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )
    manufacturer_cluster = device.endpoints[2].in_clusters[0xFD10]
    attr_id = manufacturer_cluster.AttributeDefs.current_summation.id

    class _FailRecord:
        status = foundation.Status.FAILURE
        attrid = attr_id

    with mock.patch.object(
        manufacturer_cluster,
        "_write_attributes",
        mock.AsyncMock(return_value=[[_FailRecord()], []]),
    ):
        await manufacturer_cluster.write_attributes({"current_summation": 99999})
        assert attr_id not in manufacturer_cluster._attr_cache
