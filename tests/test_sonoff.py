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
    ("mask", "expected_states"),
    [
        (
            SonoffDetachedRelayMask.Relay1,
            (True, False, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2,
            (True, True, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1
            | SonoffDetachedRelayMask.Relay2
            | SonoffDetachedRelayMask.Relay3,
            (True, True, True),
        ),
    ],
    ids=["relay1", "relay1+2", "relay1+2+3"],
)
async def test_sonoff_zbm5_relay_mask_propagation(
    zigpy_device_from_v2_quirk, mask, expected_states
):
    """Test relay mask updates propagate to local cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            },
            2: {OnOff.cluster_id: ClusterType.Server},
            3: {OnOff.cluster_id: ClusterType.Server},
        },
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
    """Test writing relay attributes translates to mask write and updates local state."""
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
    local_listener = ClusterListener(local_cluster)

    # Mock at the low level so real write_attributes runs and emits events
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

        # Verify mask was written to device
        assert mock_write.call_count == 1
        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1
        assert (
            written_attrs[0].attrid == SonoffCluster.AttributeDefs.detach_relay_mask.id
        )

        # Verify local relay states updated via AttributeWrittenEvent
        relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
        relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
        relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

        assert local_listener.attribute_updates[0] == (relay_1_attr, True)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)

        # Write relay_1_detached = False to test clearing a bit
        local_listener.attribute_updates.clear()
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: False}
        )

        written_attrs = mock_write.call_args[0][0]
        assert written_attrs[0].value.value == SonoffDetachedRelayMask(0)

        assert local_listener.attribute_updates[0] == (relay_1_attr, False)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)


async def test_sonoff_cluster_failed_write_does_not_propagate(
    zigpy_device_from_v2_quirk,
):
    """Test that a failed mask write does not update local relay states."""
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
    local_listener = ClusterListener(local_cluster)

    # Mock a failed write
    write_response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=SonoffCluster.AttributeDefs.detach_relay_mask.id,
            )
        ]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ):
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

    # Local relay states should not have been updated
    assert len(local_listener.attribute_updates) == 0


async def test_sonoff_cluster_apply_custom_configuration(zigpy_device_from_v2_quirk):
    """Test apply_custom_configuration reads mask and populates local relay states."""
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
    local_listener = ClusterListener(local_cluster)

    mask_attr = SonoffCluster.AttributeDefs.detach_relay_mask
    mask = SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2

    # Mock raw ZCL read so the full read_attributes chain runs and fires events
    read_response = foundation.ReadAttributeRecord(
        attrid=mask_attr.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(type=mask_attr.zcl_type, value=mask),
    )
    with mock.patch.object(
        sonoff_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=[[read_response]]),
    ):
        await sonoff_cluster.apply_custom_configuration()

    # Verify local relay states were populated from the read
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    assert local_listener.attribute_updates[0] == (relay_1_attr, True)
    assert local_listener.attribute_updates[1] == (relay_2_attr, True)
    assert local_listener.attribute_updates[2] == (relay_3_attr, False)
