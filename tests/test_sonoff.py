"""Tests for Sonoff ZBM5 quirks."""

from unittest import mock

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.sonoff.zbm5

zhaquirks.setup()

LOCAL_CLUSTER_ID = zhaquirks.sonoff.zbm5.SonoffInputConfigCluster.cluster_id


async def test_sonoff_zbm5_1c_cluster(zigpy_device_from_v2_quirk):
    """Test Sonoff ZBM5-1C custom cluster functionality."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    local_cluster = device.endpoints[1].in_clusters[LOCAL_CLUSTER_ID]
    sonoff_listener = ClusterListener(sonoff_cluster)
    local_listener = ClusterListener(local_cluster)

    # Test work mode attribute
    work_mode_attr = sonoff_cluster.AttributeDefs.work_mode.id
    sonoff_cluster.update_attribute(
        work_mode_attr, zhaquirks.sonoff.zbm5.SonoffWorkMode.Router
    )

    assert len(sonoff_listener.attribute_updates) == 1
    assert sonoff_listener.attribute_updates[0][0] == work_mode_attr
    assert (
        sonoff_listener.attribute_updates[0][1]
        == zhaquirks.sonoff.zbm5.SonoffWorkMode.Router
    )

    # Test relay mask conversion propagates to local cluster
    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id

    # Set relay 1 as detached
    sonoff_cluster.update_attribute(
        detach_mask_attr, zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
    )

    # SonoffCluster should have 1 update (detach_mask)
    assert len(sonoff_listener.attribute_updates) == 2
    assert sonoff_listener.attribute_updates[1][0] == detach_mask_attr

    # Local cluster should have updates for all 3 relay states
    # (3 from __init__ defaults + 3 from mask update)
    assert local_listener.attribute_updates[-3][0] == relay_1_attr
    assert local_listener.attribute_updates[-3][1] is True


async def test_sonoff_zbm5_2c_cluster(zigpy_device_from_v2_quirk):
    """Test Sonoff ZBM5-2C custom cluster functionality."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-2C-80/86",
        cluster_ids={
            1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in", 0x0006: "in"},
            2: {0x0006: "in"},
        },
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    local_cluster = device.endpoints[1].in_clusters[LOCAL_CLUSTER_ID]
    local_listener = ClusterListener(local_cluster)

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id

    # Set both relay 1 and 2 as detached
    mask = (
        zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
        | zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay2
    )
    sonoff_cluster.update_attribute(
        sonoff_cluster.AttributeDefs.detach_relay_mask.id, mask
    )

    # Last 3 updates on local cluster should be the relay states
    assert local_listener.attribute_updates[-3][0] == relay_1_attr
    assert local_listener.attribute_updates[-3][1] is True
    assert local_listener.attribute_updates[-2][0] == relay_2_attr
    assert local_listener.attribute_updates[-2][1] is True


async def test_sonoff_zbm5_3c_cluster(zigpy_device_from_v2_quirk):
    """Test Sonoff ZBM5-3C custom cluster functionality."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={
            1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in", 0x0006: "in"},
            2: {0x0006: "in"},
            3: {0x0006: "in"},
        },
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    local_cluster = device.endpoints[1].in_clusters[LOCAL_CLUSTER_ID]
    local_listener = ClusterListener(local_cluster)

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    # Set all relays as detached
    mask = (
        zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
        | zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay2
        | zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay3
    )
    sonoff_cluster.update_attribute(
        sonoff_cluster.AttributeDefs.detach_relay_mask.id, mask
    )

    # Last 3 updates on local cluster should be all relay states
    assert local_listener.attribute_updates[-3][0] == relay_1_attr
    assert local_listener.attribute_updates[-3][1] is True
    assert local_listener.attribute_updates[-2][0] == relay_2_attr
    assert local_listener.attribute_updates[-2][1] is True
    assert local_listener.attribute_updates[-1][0] == relay_3_attr
    assert local_listener.attribute_updates[-1][1] is True


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test writing relay attributes translates to mask write on SonoffCluster."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in", LOCAL_CLUSTER_ID: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    local_cluster = device.endpoints[1].in_clusters[LOCAL_CLUSTER_ID]

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.name
    detach_mask_attr_id = sonoff_cluster.AttributeDefs.detach_relay_mask.id

    # Mock the SonoffCluster's write_attributes
    with mock.patch.object(
        sonoff_cluster.__class__.__bases__[0], "write_attributes"
    ) as mock_write:
        mock_write.return_value = None

        # Write relay_1_detached = True via local cluster
        await local_cluster.write_attributes({relay_1_attr: True})

        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert detach_mask_attr_id in call_args
        assert (
            call_args[detach_mask_attr_id]
            == zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
        )
