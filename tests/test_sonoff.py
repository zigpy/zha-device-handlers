"""Tests for Sonoff ZBM5 quirks."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.zbm5 import (
    SonoffCluster,
    SonoffDetachedRelayMask,
    SonoffInputConfigCluster,
    SonoffWorkMode,
)

zhaquirks.setup()

LOCAL_CLUSTER_ID = SonoffInputConfigCluster.cluster_id


async def test_sonoff_zbm5_1c_cluster(zigpy_device_from_v2_quirk):
    """Test Sonoff ZBM5-1C custom cluster functionality."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in"}},
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    sonoff_listener = ClusterListener(sonoff_cluster)
    local_listener = ClusterListener(local_cluster)

    # Test work mode attribute
    work_mode_attr = sonoff_cluster.AttributeDefs.work_mode.id
    sonoff_cluster.update_attribute(work_mode_attr, SonoffWorkMode.Router)

    assert len(sonoff_listener.attribute_updates) == 1
    assert sonoff_listener.attribute_updates[0][0] == work_mode_attr
    assert sonoff_listener.attribute_updates[0][1] == SonoffWorkMode.Router

    # Test relay mask conversion propagates to local cluster
    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id

    sonoff_cluster.update_attribute(detach_mask_attr, SonoffDetachedRelayMask.Relay1)

    # SonoffCluster should have 1 update (detach_mask)
    assert len(sonoff_listener.attribute_updates) == 2
    assert sonoff_listener.attribute_updates[1][0] == detach_mask_attr

    assert local_listener.attribute_updates[0] == (relay_1_attr, True)


async def test_sonoff_zbm5_2c_cluster(zigpy_device_from_v2_quirk):
    """Test Sonoff ZBM5-2C relay mask propagation."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-2C-80/86",
        cluster_ids={
            1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in", OnOff.cluster_id: "in"},
            2: {OnOff.cluster_id: "in"},
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    # Set both relay 1 and 2 as detached
    mask = SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2
    sonoff_cluster.update_attribute(
        sonoff_cluster.AttributeDefs.detach_relay_mask.id, mask
    )

    assert len(local_listener.attribute_updates) == 3
    assert local_listener.attribute_updates[0] == (relay_1_attr, True)
    assert local_listener.attribute_updates[1] == (relay_2_attr, True)
    # Relay 3 not in mask, should remain attached
    assert local_listener.attribute_updates[2] == (relay_3_attr, False)


async def test_sonoff_zbm5_3c_cluster(zigpy_device_from_v2_quirk):
    """Test Sonoff ZBM5-3C relay mask propagation."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={
            1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in", OnOff.cluster_id: "in"},
            2: {OnOff.cluster_id: "in"},
            3: {OnOff.cluster_id: "in"},
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    # Set all relays as detached
    mask = (
        SonoffDetachedRelayMask.Relay1
        | SonoffDetachedRelayMask.Relay2
        | SonoffDetachedRelayMask.Relay3
    )
    sonoff_cluster.update_attribute(
        sonoff_cluster.AttributeDefs.detach_relay_mask.id, mask
    )

    assert len(local_listener.attribute_updates) == 3
    assert local_listener.attribute_updates[0] == (relay_1_attr, True)
    assert local_listener.attribute_updates[1] == (relay_2_attr, True)
    assert local_listener.attribute_updates[2] == (relay_3_attr, True)


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test writing relay attributes translates to mask write on SonoffCluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in"}},
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

        mock_write.assert_called_once()
        written_attrs = mock_write.call_args[0][0]
        assert written_attrs == {detach_mask_attr_id: SonoffDetachedRelayMask.Relay1}
