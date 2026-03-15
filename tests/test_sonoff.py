"""Tests for Sonoff ZBM5 quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.zbm5 import (
    SonoffCluster,
    SonoffDetachedRelayMask,
    SonoffInputConfigCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("model", "cluster_ids", "mask", "expected_states"),
    [
        (
            "ZBM5-1C-80/86",
            {
                1: {
                    SonoffCluster.cluster_id: ClusterType.Server,
                    SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                }
            },
            SonoffDetachedRelayMask.Relay1,
            (True, False, False),
        ),
        (
            "ZBM5-2C-80/86",
            {
                1: {
                    SonoffCluster.cluster_id: ClusterType.Server,
                    SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                    OnOff.cluster_id: ClusterType.Server,
                },
                2: {OnOff.cluster_id: ClusterType.Server},
            },
            SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2,
            (True, True, False),
        ),
        (
            "ZBM5-3C-80/86",
            {
                1: {
                    SonoffCluster.cluster_id: ClusterType.Server,
                    SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                    OnOff.cluster_id: ClusterType.Server,
                },
                2: {OnOff.cluster_id: ClusterType.Server},
                3: {OnOff.cluster_id: ClusterType.Server},
            },
            SonoffDetachedRelayMask.Relay1
            | SonoffDetachedRelayMask.Relay2
            | SonoffDetachedRelayMask.Relay3,
            (True, True, True),
        ),
    ],
    ids=["1C", "2C", "3C"],
)
async def test_sonoff_zbm5_relay_mask_propagation(
    zigpy_device_from_v2_quirk, model, cluster_ids, mask, expected_states
):
    """Test relay mask updates propagate to local cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model=model,
        cluster_ids=cluster_ids,
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    sonoff_listener = ClusterListener(sonoff_cluster)
    local_listener = ClusterListener(local_cluster)

    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    sonoff_cluster.update_attribute(detach_mask_attr, mask)

    assert len(sonoff_listener.attribute_updates) == 1
    assert sonoff_listener.attribute_updates[0][0] == detach_mask_attr

    assert len(local_listener.attribute_updates) == 3
    assert local_listener.attribute_updates[0] == (relay_1_attr, expected_states[0])
    assert local_listener.attribute_updates[1] == (relay_2_attr, expected_states[1])
    assert local_listener.attribute_updates[2] == (relay_3_attr, expected_states[2])


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test writing relay attributes translates to mask write on SonoffCluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.name
    detach_mask_attr_id = SonoffCluster.AttributeDefs.detach_relay_mask.id

    with mock.patch.object(
        sonoff_cluster,
        "write_attributes",
        mock.AsyncMock(
            return_value=[
                foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
            ]
        ),
    ) as mock_write:
        await local_cluster.write_attributes({relay_1_attr: True})

        assert mock_write.call_count == 1
        assert mock_write.call_args[0][0] == {
            detach_mask_attr_id: SonoffDetachedRelayMask.Relay1
        }
