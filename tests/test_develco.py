"""Tests for Develco/Frient."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms import EntityCategory
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.develco.humidity import HumidityPowerConfiguration
from zhaquirks.develco.power_plug import WholeDegreeDeviceTemperature

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

    # send mfr-specific attribute report with divisor attribute ID — should not update
    # the ZCL divisor
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

    # An attribute update with the divisor ID is emitted, but as the manufacturer bit
    # is set, the value in the attribute cache for the divisor should NOT be updated.
    # The quirk keeps forcing the divisor to 1000.
    assert len(metering_listener.attribute_updates) == 1
    assert metering_listener.attribute_updates == [
        (Metering.AttributeDefs.divisor.id, 512)
    ]
    assert metering_cluster.get(Metering.AttributeDefs.divisor) == 1000
    with pytest.raises(KeyError):
        metering_cluster._attr_cache.get_value(Metering.AttributeDefs.divisor)

    # It is only present in the legacy cache, as the definition for the manufacturer
    # specific attribute does not yet exist in the quirk.
    assert metering_cluster._attr_cache.get(Metering.AttributeDefs.divisor.id) == 512

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

    # attribute_updated events should be emitted (5 due to previous mfr-specific report)
    assert len(metering_listener.attribute_updates) == 5
    assert (
        metering_cluster.get(Metering.AttributeDefs.current_summ_delivered.id)
        == 30_723_080
    )
    assert metering_cluster.get(Metering.AttributeDefs.current_summ_received.id) == 0
    assert metering_cluster.get(Metering.AttributeDefs.instantaneous_demand.id) == 4001
    assert metering_cluster.get(Metering.AttributeDefs.status.id) == 0


async def test_mfg_cluster_divisor_report_default_response(zigpy_device_from_v2_quirk):
    """Test Frient EMI Norwegian HAN divisor reports are acknowledged and ignored."""
    device = zigpy_device_from_v2_quirk("frient A/S", "EMIZB-132", endpoint_ids=[1, 2])

    metering_cluster = device.endpoints[2].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)

    # Synthetic frame, not a captured device report: the real divisor report sets
    # Disable Default Response, so default response requested is set here on purpose.
    # Frame: 0x08 (non-mfr-specific, server-to-client, default response requested),
    #        TSN=1, cmd=0x0a (Report_Attributes), attr=0x0302 (divisor), value=512
    with mock.patch.object(metering_cluster, "send_default_rsp") as default_rsp_mock:
        device.packet_received(
            t.ZigbeePacket(
                profile_id=260,
                cluster_id=Metering.cluster_id,
                src_ep=2,
                dst_ep=2,
                data=t.SerializableBytes(b"\x08\x01\x0a\x02\x03\x22\x00\x02\x00"),
            )
        )

    default_rsp_mock.assert_called_once_with(mock.ANY, foundation.Status.SUCCESS)
    assert metering_listener.attribute_updates == [
        (Metering.AttributeDefs.divisor.id, 512)
    ]
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == 1000


async def test_mfg_cluster_stale_divisor(zigpy_device_from_v2_quirk):
    """Test Frient EMI Norwegian HAN ignores a stale cached divisor."""
    device = zigpy_device_from_v2_quirk("frient A/S", "EMIZB-132", endpoint_ids=[1, 2])
    metering_cluster = device.endpoints[2].smartenergy_metering

    # Installs from before zigpy 0.91 can have the interface mode cached as divisor
    metering_cluster._attr_cache.set_value(Metering.AttributeDefs.divisor, 512)
    assert metering_cluster.get(Metering.AttributeDefs.divisor.name) == 1000


async def test_hmszb_120_power_config_battery_percent_from_voltage(
    zigpy_device_from_v2_quirk,
):
    """Test battery percent is derived from cached voltage."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "HMSZB-120",
        endpoint_ids=[38],
        cluster_ids={38: {PowerConfiguration.cluster_id: ClusterType.Server}},
    )

    power = device.endpoints[38].power
    assert isinstance(power, HumidityPowerConfiguration)
    assert power.MIN_VOLTS == 2.3
    assert power.MAX_VOLTS == 3.0

    # 2.8 V, within the 2.3–3.0 V bounds: (2.8 - 2.3) / (3.0 - 2.3) * 200 = 143 (half percent)
    power.update_attribute(PowerConfiguration.AttributeDefs.battery_voltage.id, 28)

    assert (
        power.get(PowerConfiguration.AttributeDefs.battery_percentage_remaining.id)
        == 143
    )


async def test_frient_smart_plug_device_temperature():
    """Test that the device temperature is not divided by 100."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "frient-a-s-splzb-141-0x00020009.json", DEVICE_REGISTRY
        )
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="00:15:bc:00:2f:02:19:79-2-2"
        )

        assert type(entity) is WholeDegreeDeviceTemperature
        assert entity.native_value == 32
        assert entity.entity_category == EntityCategory.DIAGNOSTIC
