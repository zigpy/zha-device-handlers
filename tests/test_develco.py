"""Tests for Develco/Frient."""

from unittest import mock

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import TypeValue

import zhaquirks

zhaquirks.setup()


async def test_frient_emi(zigpy_device_from_v2_quirk):
    """Test that the EMI correctly forwards custom attributes."""
    device = zigpy_device_from_v2_quirk("frient A/S", "EMIZB-141", endpoint_ids=[1, 2])

    metering_cluster = device.endpoints[2].smartenergy_metering
    # metering_listener = ClusterListener(metering_cluster)
    pulse_config_attr_id = metering_cluster.AttributeDefs.pulse_configuration.id

    # todo: likely replace with read/write attribute mocks for proper result
    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        # read custom attribute
        result = await metering_cluster.read_attributes([pulse_config_attr_id])
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            True,
            foundation.GeneralCommand.Read_Attributes,
            mock.ANY,  # todo: fix?
            [0x0300],
            manufacturer=0x1015,
            expect_reply=True,
            tsn=None,
        )

        # assert result == ({pulse_config_attr_id: "done"}, {})
        assert result == ({}, {0x0300: foundation.Status.SUCCESS})  # todo: fix?
        request_mock.reset_mock()

        # write custom attribute
        result = await metering_cluster.write_attributes({pulse_config_attr_id: "42"})
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            True,
            foundation.GeneralCommand.Write_Attributes,
            mock.ANY,  # todo: fix?
            [
                foundation.Attribute(
                    attrid=0x0300, value=TypeValue(type=t.uint16_t, value=42)
                )
            ],
            manufacturer=0x1015,
            expect_reply=True,
            tsn=None,
        )
        assert result == (foundation.Status.SUCCESS, "done")  # todo: fix?
        request_mock.reset_mock()

        # read non-custom attribute
        result = await metering_cluster.read_attributes(
            [metering_cluster.AttributeDefs.current_summ_delivered.id]
        )
        assert request_mock.call_count == 1
        assert request_mock.call_args == mock.call(
            True,
            foundation.GeneralCommand.Read_Attributes,
            mock.ANY,  # todo: fix?
            [metering_cluster.AttributeDefs.current_summ_delivered.id],
            manufacturer=None,
            expect_reply=True,
            tsn=None,
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
            True,
            foundation.GeneralCommand.Write_Attributes,
            mock.ANY,  # todo: fix?
            [
                foundation.Attribute(
                    attrid=metering_cluster.AttributeDefs.current_summ_delivered.id,
                    value=TypeValue(type=mock.ANY, value=100),
                )
            ],  # todo: fix type
            manufacturer=None,
            expect_reply=True,
            tsn=None,
        )
        assert result == (foundation.Status.SUCCESS, "done")
