"""Tests for Develco/Frient."""

from unittest import mock

import zigpy.quirks
from zigpy.quirks.v2 import EntityPlatform
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import DeviceTemperature, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.develco.power_plug import MANUFACTURER_CODE, VendorOnOff

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


async def test_frient_power_plug_defaults(zigpy_device_from_v2_quirk):
    """Test power plug initializes mode values."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SPLZB-131",
        endpoint_ids=[1, 2],
        cluster_ids={2: {OnOff.cluster_id: ClusterType.Server}},
    )

    on_off = device.endpoints[2].on_off
    assert isinstance(on_off, VendorOnOff)
    assert on_off.get(VendorOnOff.AttributeDefs.mode_on_value.id) == 0
    assert on_off.get(VendorOnOff.AttributeDefs.mode_off_value.id) == 0


async def test_frient_power_plug_safe_mode_writes(zigpy_device_from_v2_quirk):
    """Test mode writes invoke manufacturer safe-mode commands."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SPLZB-131",
        endpoint_ids=[1, 2],
        cluster_ids={
            2: {
                OnOff.cluster_id: ClusterType.Server,
                DeviceTemperature.cluster_id: ClusterType.Server,
                ElectricalMeasurement.cluster_id: ClusterType.Server,
            }
        },
    )

    on_off = device.endpoints[2].on_off

    attrs_on = {VendorOnOff.AttributeDefs.mode_on_value.id: 5}
    attrs_off = {VendorOnOff.AttributeDefs.mode_off_value.name: 7}
    attrs_on_name = {VendorOnOff.AttributeDefs.mode_on_value.name: 9}
    attrs_off_id = {VendorOnOff.AttributeDefs.mode_off_value.id: 11}

    with mock.patch.object(
        VendorOnOff, "_send_safe_mode", new=mock.AsyncMock()
    ) as send_safe_mode:
        await on_off.write_attributes(attrs_on)
        send_safe_mode.assert_called_once_with(0x01, 5)
        assert on_off.get(VendorOnOff.AttributeDefs.mode_on_value.id) == 5
        assert attrs_on == {VendorOnOff.AttributeDefs.mode_on_value.id: 5}

        send_safe_mode.reset_mock()

        await on_off.write_attributes(attrs_off)
        send_safe_mode.assert_called_once_with(0x00, 7)
        assert on_off.get(VendorOnOff.AttributeDefs.mode_off_value.id) == 7
        assert attrs_off == {VendorOnOff.AttributeDefs.mode_off_value.name: 7}

        send_safe_mode.reset_mock()

        await on_off.write_attributes(attrs_on_name)
        send_safe_mode.assert_called_once_with(0x01, 9)
        assert on_off.get(VendorOnOff.AttributeDefs.mode_on_value.id) == 9
        assert attrs_on_name == {VendorOnOff.AttributeDefs.mode_on_value.name: 9}

        send_safe_mode.reset_mock()

        await on_off.write_attributes(attrs_off_id)
        send_safe_mode.assert_called_once_with(0x00, 11)
        assert on_off.get(VendorOnOff.AttributeDefs.mode_off_value.id) == 11
        assert attrs_off_id == {VendorOnOff.AttributeDefs.mode_off_value.id: 11}


async def test_frient_power_plug_send_safe_mode_request(zigpy_device_from_v2_quirk):
    """Test safe mode command uses manufacturer code and no reply."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SPLZB-131",
        endpoint_ids=[1, 2],
        cluster_ids={2: {OnOff.cluster_id: ClusterType.Server}},
    )

    on_off = device.endpoints[2].on_off

    with mock.patch.object(on_off, "request", new=mock.AsyncMock()) as request_mock:
        await on_off._send_safe_mode(0x01, 4)

    request_mock.assert_called_once()
    call_args = request_mock.call_args
    assert call_args.args[0] is False
    assert call_args.args[1] == 0x01
    assert call_args.kwargs["manufacturer"] == MANUFACTURER_CODE
    assert call_args.kwargs["expect_reply"] is False
    assert call_args.kwargs["mode"] == 4


async def test_frient_power_plug_write_attributes_passthrough(
    zigpy_device_from_v2_quirk,
):
    """Test non-vendor writes pass kwargs through to base implementation."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SPLZB-131",
        endpoint_ids=[1, 2],
        cluster_ids={2: {OnOff.cluster_id: ClusterType.Server}},
    )

    on_off = device.endpoints[2].on_off
    status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[status]),
    ) as write_mock:
        result = await on_off.write_attributes(
            {OnOff.AttributeDefs.on_off.id: 1},
            timeout=3,
        )

    write_mock.assert_called_once()
    assert write_mock.call_args.args[0] == {OnOff.AttributeDefs.on_off.id: 1}
    assert write_mock.call_args.kwargs["timeout"] == 3
    assert result == [status]


async def test_frient_power_plug_write_attributes_mixed(
    zigpy_device_from_v2_quirk,
):
    """Test vendor and standard writes can be combined without mutation."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SPLZB-131",
        endpoint_ids=[1, 2],
        cluster_ids={2: {OnOff.cluster_id: ClusterType.Server}},
    )

    on_off = device.endpoints[2].on_off
    status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    attrs = {
        VendorOnOff.AttributeDefs.mode_on_value.id: 4,
        OnOff.AttributeDefs.on_off.id: 0,
    }

    with (
        mock.patch.object(
            VendorOnOff, "_send_safe_mode", new=mock.AsyncMock()
        ) as send_safe_mode,
        mock.patch(
            "zigpy.quirks.CustomCluster.write_attributes",
            new=mock.AsyncMock(return_value=[status]),
        ) as write_mock,
    ):
        result = await on_off.write_attributes(attrs, priority=2)

    send_safe_mode.assert_called_once_with(0x01, 4)
    write_mock.assert_called_once()
    assert write_mock.call_args.args[0] == {OnOff.AttributeDefs.on_off.id: 0}
    assert write_mock.call_args.kwargs["priority"] == 2
    assert result == [status]
    assert attrs == {
        VendorOnOff.AttributeDefs.mode_on_value.id: 4,
        OnOff.AttributeDefs.on_off.id: 0,
    }


async def test_frient_power_plug_write_attributes_multiple_vendor(
    zigpy_device_from_v2_quirk,
):
    """Test multiple vendor mode writes are processed together."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SPLZB-131",
        endpoint_ids=[1, 2],
        cluster_ids={2: {OnOff.cluster_id: ClusterType.Server}},
    )

    on_off = device.endpoints[2].on_off
    attrs = {
        VendorOnOff.AttributeDefs.mode_on_value.id: 12,
        VendorOnOff.AttributeDefs.mode_off_value: 34,
    }

    with (
        mock.patch.object(
            VendorOnOff, "_send_safe_mode", new=mock.AsyncMock()
        ) as send_safe_mode,
        mock.patch(
            "zigpy.quirks.CustomCluster.write_attributes",
            new=mock.AsyncMock(),
        ) as write_mock,
    ):
        result = await on_off.write_attributes(attrs)

    send_safe_mode.assert_has_calls(
        [
            mock.call(0x01, 12),
            mock.call(0x00, 34),
        ],
        any_order=False,
    )
    write_mock.assert_not_called()
    assert on_off.get(VendorOnOff.AttributeDefs.mode_on_value.id) == 12
    assert on_off.get(VendorOnOff.AttributeDefs.mode_off_value.id) == 34
    assert attrs == {
        VendorOnOff.AttributeDefs.mode_on_value.id: 12,
        VendorOnOff.AttributeDefs.mode_off_value: 34,
    }
    assert result == [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


def _get_power_plug_entry():
    entries = zigpy.quirks.DEVICE_REGISTRY.registry_v2.get(
        ("frient A/S", "SPLZB-131"),
        [],
    )
    assert entries, "Power plug quirk not registered in v2 registry"
    return entries[0]


def test_frient_power_plug_entity_metadata() -> None:
    """Test power plug entity metadata is registered as expected."""
    entry = _get_power_plug_entry()

    mode_on = next(
        meta for meta in entry.entity_metadata if meta.translation_key == "mode_on"
    )
    assert mode_on.entity_platform is EntityPlatform.NUMBER
    assert mode_on.cluster_id == OnOff.cluster_id
    assert mode_on.endpoint_id == 2
    assert mode_on.unique_id_suffix == "mode_on"

    mode_off = next(
        meta for meta in entry.entity_metadata if meta.translation_key == "mode_off"
    )
    assert mode_off.entity_platform is EntityPlatform.NUMBER
    assert mode_off.cluster_id == OnOff.cluster_id
    assert mode_off.endpoint_id == 2
    assert mode_off.unique_id_suffix == "mode_off"

    dev_temp = next(
        meta
        for meta in entry.entity_metadata
        if meta.translation_key == "device_temperature"
    )
    assert dev_temp.entity_platform is EntityPlatform.SENSOR
    assert dev_temp.cluster_id == DeviceTemperature.cluster_id
    assert dev_temp.endpoint_id == 2
    if hasattr(dev_temp, "divisor"):
        assert dev_temp.divisor == 1

    return_to_state = next(
        meta
        for meta in entry.entity_metadata
        if meta.translation_key == "return_to_state"
    )
    assert return_to_state.entity_platform is EntityPlatform.BINARY_SENSOR
    assert return_to_state.cluster_id == OnOff.cluster_id
    assert return_to_state.endpoint_id == 2


def test_frient_power_plug_prevents_default_entities() -> None:
    """Test power plug prevents default entities for temp and power clusters."""
    entry = _get_power_plug_entry()

    prevented = list(entry.disabled_default_entities)
    assert prevented, "No disabled default entity metadata found"

    def _matches(item, cluster_id):
        return (
            getattr(item, "cluster_id", None) == cluster_id
            and getattr(item, "endpoint_id", None) == 2
        )

    assert any(_matches(item, DeviceTemperature.cluster_id) for item in prevented)
    assert any(_matches(item, ElectricalMeasurement.cluster_id) for item in prevented)
