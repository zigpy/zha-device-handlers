"""Tests for the SONOFF ZBMINIL2 device."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import KeepAlive

import zhaquirks
from zhaquirks.sonoff.zbminil2 import (
    ZBMINIL2_TRIGGER_MODE_FW_VERSION,
    SonoffZBMiniL2Cluster,
    SonoffZBMiniL2TriggerType,
)

zhaquirks.setup()

DATA_TYPE_UINT8 = foundation.DataTypeId.uint8
ZBMINIL2_CLUSTERS = {1: {SonoffZBMiniL2Cluster.cluster_id: ClusterType.Server}}


@pytest.mark.parametrize(
    ("firmware_version", "trigger_mode_supported"),
    [
        # a device that does not report a firmware version gets the base quirk
        (None, False),
        (0x0000100E, False),  # v1.0.14
        (ZBMINIL2_TRIGGER_MODE_FW_VERSION - 1, False),
        (ZBMINIL2_TRIGGER_MODE_FW_VERSION, True),  # v1.1.2
        (ZBMINIL2_TRIGGER_MODE_FW_VERSION + 1, True),
    ],
)
def test_sonoff_zbminil2_quirk_selection(
    zigpy_device_from_v2_quirk, firmware_version, trigger_mode_supported
):
    """Test the trigger mode is only exposed on supported firmware."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "ZBMINIL2",
        cluster_ids=ZBMINIL2_CLUSTERS,
        firmware_version=firmware_version,
    )

    endpoint = device.endpoints[1]

    # the KeepAlive client cluster is added for every firmware version
    assert KeepAlive.cluster_id in endpoint.out_clusters

    ewelink_cluster = endpoint.in_clusters[SonoffZBMiniL2Cluster.cluster_id]
    assert isinstance(ewelink_cluster, SonoffZBMiniL2Cluster) is trigger_mode_supported

    entry = DEVICE_REGISTRY.match_entry(device)
    entity_attributes = [
        metadata.attribute_name
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        if metadata.cluster_id == SonoffZBMiniL2Cluster.cluster_id
    ]
    assert (
        SonoffZBMiniL2Cluster.AttributeDefs.external_trigger_mode.name
        in entity_attributes
    ) is trigger_mode_supported


@pytest.mark.parametrize(
    ("mode", "raw_value"),
    [
        (SonoffZBMiniL2TriggerType.Edge_trigger, 0x00),
        (SonoffZBMiniL2TriggerType.Pulse_trigger, 0x01),
    ],
)
async def test_sonoff_zbminil2_write_trigger_mode(
    zigpy_device_from_v2_quirk, mode, raw_value
):
    """Test the trigger mode is written as uint8 without a manufacturer code."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "ZBMINIL2",
        cluster_ids=ZBMINIL2_CLUSTERS,
        firmware_version=ZBMINIL2_TRIGGER_MODE_FW_VERSION,
    )
    ewelink_cluster = device.endpoints[1].ewelink
    attr = SonoffZBMiniL2Cluster.AttributeDefs.external_trigger_mode

    request_patch = mock.patch("zigpy.device.Device.request", mock.AsyncMock())
    with request_patch as request_mock:
        # not a valid response, we only care about the outgoing request
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await ewelink_cluster.write_attributes({attr.name: mode})

    assert request_mock.call_count == 1
    assert request_mock.call_args[1]["cluster"] == SonoffZBMiniL2Cluster.cluster_id

    zcl_header, attr_data = foundation.ZCLHeader.deserialize(
        request_mock.call_args[1]["data"]
    )
    assert zcl_header.frame_control.is_manufacturer_specific == 0
    assert zcl_header.manufacturer is None
    assert zcl_header.command_id == foundation.GeneralCommand.Write_Attributes
    # attribute id (LE), uint8 data type, value
    assert attr_data == bytes([0x16, 0x00, DATA_TYPE_UINT8, raw_value])
