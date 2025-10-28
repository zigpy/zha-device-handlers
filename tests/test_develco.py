"""Tests for Develco/Frient."""

from unittest import mock

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks

zhaquirks.setup()


async def test_frient_emi(zigpy_device_from_v2_quirk):
    """Test that the EMI correctly forwards custom attributes."""
    # TODO: fix/improve

    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )

    metering_cluster = device.endpoints[2].smartenergy_metering
    # metering_listener = ClusterListener(metering_cluster)

    manufacturer_cluster = device.endpoints[2].in_clusters[0xFD10]
    # manufacturer_listener = ClusterListener(manufacturer_cluster)

    pulse_config_attr_id = manufacturer_cluster.AttributeDefs.pulse_configuration.id

    async def send_packet(packet: t.ZigbeePacket):
        # TODO: maybe use
        pass

    device.application.send_packet = mock.AsyncMock(side_effect=send_packet)

    request_patch = mock.patch("zigpy.device.Device.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        # read custom attribute
        result = await manufacturer_cluster.read_attributes([pulse_config_attr_id])
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            profile=None,
            cluster=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            sequence=mock.ANY,
            data=b"\x04\xd2\x04\x01\x00\x00\x03",  # TODO: make data interpretable
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )

        # assert result == ({pulse_config_attr_id: "done"}, {})
        assert result == ({}, {0x0300: foundation.Status.SUCCESS})
        request_mock.reset_mock()

        # write custom attribute
        result = await manufacturer_cluster.write_attributes(
            {pulse_config_attr_id: "42"}
        )
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            profile=None,
            cluster=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            sequence=mock.ANY,
            data=b"\x04\xd2\x04\x02\x02\x00\x03!*\x00",
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )
        assert result == (foundation.Status.SUCCESS, "done")
        request_mock.reset_mock()

        # read non-custom attribute
        result = await metering_cluster.read_attributes(
            [metering_cluster.AttributeDefs.current_summ_delivered.id]
        )
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            profile=None,
            cluster=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            sequence=mock.ANY,
            data=b"\x00\x03\x00\x00\x00",
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )
        assert result == (
            {},
            {
                metering_cluster.AttributeDefs.current_summ_delivered.id: foundation.Status.SUCCESS
            },
        )
        request_mock.reset_mock()

        # write non-custom attribute
        result = await metering_cluster.write_attributes(
            {metering_cluster.AttributeDefs.current_summ_delivered.id: 100}
        )
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            profile=None,
            cluster=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            sequence=mock.ANY,
            data=b"\x00\x04\x02\x00\x00%d\x00\x00\x00\x00\x00",
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )

        assert result == (foundation.Status.SUCCESS, "done")
