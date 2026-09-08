"""Tests for Tuya/BSEED TS0726 scene switch quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.tuya import TUYA_CLUSTER_E000_ID, TUYA_CLUSTER_E001_ID
from zhaquirks.tuya.ts0726 import BseedTS0726OnOffCluster, BseedTS0726OptionsCluster


@pytest.mark.parametrize(
    ("manufacturer", "endpoint_ids", "expected_endpoint_count"),
    [
        ("_TZ3002_jn2x20tg", [1], 1),
        ("_TZ3002_zjuvw9zf", [1, 2], 2),
    ],
)
def test_bseed_ts0726_clusters(
    zigpy_device_from_v2_quirk, manufacturer, endpoint_ids, expected_endpoint_count
):
    """Test TS0726 clusters are replaced."""

    cluster_ids = {
        endpoint_id: {
            OnOff.cluster_id: ClusterType.Server,
            TUYA_CLUSTER_E001_ID: ClusterType.Server,
        }
        for endpoint_id in endpoint_ids
    }
    cluster_ids[1][TUYA_CLUSTER_E000_ID] = ClusterType.Server

    device = zigpy_device_from_v2_quirk(
        manufacturer,
        "TS0726",
        cluster_ids=cluster_ids,
    )

    for endpoint_id in range(1, expected_endpoint_count + 1):
        assert isinstance(
            device.endpoints[endpoint_id].in_clusters[OnOff.cluster_id],
            BseedTS0726OnOffCluster,
        )
        assert isinstance(
            device.endpoints[endpoint_id].in_clusters[TUYA_CLUSTER_E001_ID],
            BseedTS0726OptionsCluster,
        )


@pytest.mark.parametrize(
    ("manufacturer", "endpoint_id", "expected_command"),
    [
        ("_TZ3002_jn2x20tg", 1, "scene_1"),
        ("_TZ3002_zjuvw9zf", 1, "scene_1"),
        ("_TZ3002_zjuvw9zf", 2, "scene_2"),
    ],
)
def test_bseed_ts0726_scene_events(
    zigpy_device_from_v2_quirk, manufacturer, endpoint_id, expected_command
):
    """Test TS0726 scene mode events."""

    device = zigpy_device_from_v2_quirk(
        manufacturer,
        "TS0726",
        endpoint_ids=[1, 2],
        cluster_ids={
            1: {OnOff.cluster_id: ClusterType.Server},
            2: {OnOff.cluster_id: ClusterType.Server},
        },
    )
    cluster = device.endpoints[endpoint_id].in_clusters[OnOff.cluster_id]
    cluster.send_default_rsp = mock.MagicMock()
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    hdr = foundation.ZCLHeader.cluster(tsn=1, command_id=0xFD)
    cluster.handle_cluster_request(hdr, [0])
    cluster.handle_cluster_request(hdr, [0])

    assert listener.zha_send_event.call_args == mock.call(expected_command, [])
    assert listener.zha_send_event.call_count == 1


def test_bseed_ts0726_forwards_standard_on_off_requests(zigpy_device_from_v2_quirk):
    """Test standard OnOff commands are handled normally."""

    device = zigpy_device_from_v2_quirk(
        "_TZ3002_jn2x20tg",
        "TS0726",
        cluster_ids={1: {OnOff.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[OnOff.cluster_id]

    hdr = foundation.ZCLHeader.cluster(tsn=2, command_id=OnOff.ServerCommandDefs.on.id)

    with mock.patch.object(OnOff, "handle_cluster_request", autospec=True) as handler:
        cluster.handle_cluster_request(hdr, [])

    handler.assert_called_once_with(cluster, hdr, [], dst_addressing=None)
