"""Tests for Schneider Electric devices."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Ballast
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zdo.types import NodeDescriptor

from tests.common import ClusterListener
from zhaquirks.builder.metadata import ZCLEnumMetadata
from zhaquirks.schneiderelectric import (
    SE_MANUF_ID,
    SE_MANUF_NAME,
    SESwitchConfiguration,
    SESwitchIndication,
)
import zhaquirks.schneiderelectric.outlet

zhaquirks.setup()

# Endpoints and clusters of a CH/DIMMER/1 (firmware 0x020307ff)
CH_DIMMER_1_CLUSTERS = {
    3: {
        Basic.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        Groups.cluster_id: ClusterType.Server,
        Scenes.cluster_id: ClusterType.Server,
        OnOff.cluster_id: ClusterType.Server,
        LevelControl.cluster_id: ClusterType.Server,
        Ballast.cluster_id: ClusterType.Server,
        Diagnostic.cluster_id: ClusterType.Server,
        Ota.cluster_id: ClusterType.Client,
    },
    21: {
        Basic.cluster_id: ClusterType.Server,
        Identify.cluster_id: ClusterType.Server,
        Diagnostic.cluster_id: ClusterType.Server,
        SESwitchConfiguration.cluster_id: ClusterType.Server,
        # Identify is also a client cluster, which the fixture can't express
        Groups.cluster_id: ClusterType.Client,
        Scenes.cluster_id: ClusterType.Client,
        OnOff.cluster_id: ClusterType.Client,
        LevelControl.cluster_id: ClusterType.Client,
        WindowCovering.cluster_id: ClusterType.Client,
    },
    242: {GreenPowerProxy.cluster_id: ClusterType.Client},
}


async def test_ch_dimmer_1_switch_indication(zigpy_device_from_v2_quirk):
    """Test the CH/DIMMER/1 LED indicator can be read and written."""
    device = zigpy_device_from_v2_quirk(
        SE_MANUF_NAME, "CH/DIMMER/1", cluster_ids=CH_DIMMER_1_CLUSTERS
    )
    device.node_desc = NodeDescriptor(manufacturer_code=SE_MANUF_ID)

    # only the switch configuration cluster on endpoint 21 is replaced
    switch_cfg = device.endpoints[21].in_clusters[SESwitchConfiguration.cluster_id]
    assert type(switch_cfg) is SESwitchConfiguration
    assert type(device.endpoints[3].in_clusters[OnOff.cluster_id]) is OnOff
    assert type(device.endpoints[3].in_clusters[Ballast.cluster_id]) is Ballast
    assert type(device.endpoints[21].in_clusters[Basic.cluster_id]) is Basic

    # the LED indicator is exposed as a select entity on endpoint 21
    entry = DEVICE_REGISTRY.match_entry(device)
    (metadata,) = entry.zha_device_factory.quirk_definition.entity_metadata
    assert isinstance(metadata, ZCLEnumMetadata)
    assert metadata.endpoint_id == 21
    assert metadata.cluster_id == SESwitchConfiguration.cluster_id
    assert (
        metadata.attribute_name
        == SESwitchConfiguration.AttributeDefs.se_switch_indication.name
    )
    assert metadata.enum is SESwitchIndication
    assert metadata.translation_key == "switch_indication"

    attr = SESwitchConfiguration.AttributeDefs.se_switch_indication
    read_rsp = [
        [
            foundation.ReadAttributeRecord(
                attr.id,
                foundation.Status.SUCCESS,
                foundation.TypeValue(None, SESwitchIndication.AlwaysOn),
            )
        ]
    ]
    write_rsp = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    with mock.patch.object(
        device, "request", mock.AsyncMock(side_effect=[read_rsp, write_rsp])
    ) as request_mock:
        success, failure = await switch_cfg.read_attributes([attr.name])
        assert success == {attr.name: SESwitchIndication.AlwaysOn}
        assert failure == {}

        await switch_cfg.write_attributes({attr.name: SESwitchIndication.InverseOfLoad})
        assert switch_cfg.get(attr.name) == SESwitchIndication.InverseOfLoad

    assert request_mock.call_count == 2
    read_call, write_call = request_mock.call_args_list

    for call, command_id, payload in (
        # attribute 0x0000
        (read_call, foundation.GeneralCommand.Read_Attributes, b"\x00\x00"),
        # attribute 0x0000, enum8 (0x30), InverseOfLoad (0x02)
        (write_call, foundation.GeneralCommand.Write_Attributes, b"\x00\x00\x30\x02"),
    ):
        assert call.kwargs["cluster"] == SESwitchConfiguration.cluster_id
        assert call.kwargs["src_ep"] == 21
        assert call.kwargs["dst_ep"] == 21
        hdr, data = foundation.ZCLHeader.deserialize(call.kwargs["data"])
        assert hdr.frame_control.is_manufacturer_specific
        assert hdr.manufacturer == SE_MANUF_ID
        assert hdr.command_id == command_id
        assert data == payload


async def test_1gang_shutter_1_go_to_lift_percentage_cmd(zigpy_device_from_v2_quirk):
    """Asserts that the go_to_lift_percentage command inverts the percentage value."""

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model="1GANG/SHUTTER/1",
        endpoint_ids=[5, 21],
    )
    window_covering_cluster = device.endpoints[5].window_covering

    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())
    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await window_covering_cluster.go_to_lift_percentage(58)

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
        )
        assert request_mock.call_args[0][3] == 42  # 100 - 58


async def test_1gang_shutter_1_unpatched_cmd(zigpy_device_from_v2_quirk):
    """Asserts that unpatched ZCL commands keep working."""

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model="1GANG/SHUTTER/1",
        endpoint_ids=[5, 21],
    )
    window_covering_cluster = device.endpoints[5].window_covering

    p = mock.patch.object(window_covering_cluster, "request", mock.AsyncMock())
    with p as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await window_covering_cluster.up_open()

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.up_open.id
        )


async def test_1gang_shutter_1_lift_percentage_updates(zigpy_device_from_v2_quirk):
    """Asserts that updates to the ``current_position_lift_percentage`` attribute.

    (e.g., by the device) invert the reported percentage value.
    """

    device = zigpy_device_from_v2_quirk(
        manufacturer=SE_MANUF_NAME,
        model="1GANG/SHUTTER/1",
        endpoint_ids=[5, 21],
    )
    window_covering_cluster = device.endpoints[5].window_covering
    cluster_listener = ClusterListener(window_covering_cluster)

    window_covering_cluster.update_attribute(
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        77,
    )

    assert len(cluster_listener.attribute_updates) == 1
    assert cluster_listener.attribute_updates[0] == (
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        23,  # 100 - 77
    )
    assert len(cluster_listener.cluster_commands) == 0


@pytest.mark.parametrize("quirk", (zhaquirks.schneiderelectric.outlet.SocketOutlet,))
async def test_schneider_device_temp(zigpy_device_from_quirk, quirk):
    """Test that instant demand is divided by 1000."""
    device = zigpy_device_from_quirk(quirk)

    metering_cluster = device.endpoints[6].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)
    instantaneous_demand_attr_id = Metering.AttributeDefs.instantaneous_demand.id
    summation_delivered_attr_id = Metering.AttributeDefs.current_summ_delivered.id

    # verify instant demand is divided by 1000
    metering_cluster.update_attribute(instantaneous_demand_attr_id, 25000)
    assert len(metering_listener.attribute_updates) == 1
    assert metering_listener.attribute_updates[0][0] == instantaneous_demand_attr_id
    assert metering_listener.attribute_updates[0][1] == 25  # divided by 1000

    # verify other attributes are not modified
    metering_cluster.update_attribute(summation_delivered_attr_id, 25)
    assert len(metering_listener.attribute_updates) == 2
    assert metering_listener.attribute_updates[1][0] == summation_delivered_attr_id
    assert metering_listener.attribute_updates[1][1] == 25  # not modified
