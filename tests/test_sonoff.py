"""Tests for Sonoff ZBM5 quirks."""

from unittest import mock

import pytest

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.sonoff.zbm5

zhaquirks.setup()


@pytest.mark.parametrize("quirk", (zhaquirks.sonoff.zbm5.zbm_1c_quirk,))
async def test_sonoff_zbm5_1c_cluster(zigpy_device_from_v2_quirk, quirk):
    """Test Sonoff ZBM5-1C custom cluster functionality."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    sonoff_listener = ClusterListener(sonoff_cluster)

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

    # Test relay mask conversion
    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = sonoff_cluster.AttributeDefs.relay_1_detached.id

    # Set relay 1 as detached
    sonoff_cluster.update_attribute(
        detach_mask_attr, zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
    )

    # Should have 4 updates: detach_mask, relay_1_detached, relay_2_detached,
    # relay_3_detached
    assert len(sonoff_listener.attribute_updates) == 5
    assert sonoff_listener.attribute_updates[1][0] == detach_mask_attr
    assert (
        sonoff_listener.attribute_updates[1][1]
        == zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
    )
    assert sonoff_listener.attribute_updates[2][0] == relay_1_attr
    assert sonoff_listener.attribute_updates[2][1] is True


@pytest.mark.parametrize("quirk", (zhaquirks.sonoff.zbm5.zbm_2c_quirk,))
async def test_sonoff_zbm5_2c_cluster(zigpy_device_from_v2_quirk, quirk):
    """Test Sonoff ZBM5-2C custom cluster functionality."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-2C-80/86",
        cluster_ids={1: {0xFC11: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    sonoff_listener = ClusterListener(sonoff_cluster)

    # Test relay mask with multiple relays
    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = sonoff_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = sonoff_cluster.AttributeDefs.relay_2_detached.id

    # Set both relay 1 and 2 as detached
    mask = (
        zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
        | zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay2
    )
    sonoff_cluster.update_attribute(detach_mask_attr, mask)

    # Should have updates for detach_mask, relay_1_detached, relay_2_detached,
    # relay_3_detached
    assert len(sonoff_listener.attribute_updates) == 4
    assert sonoff_listener.attribute_updates[0][0] == detach_mask_attr
    assert sonoff_listener.attribute_updates[0][1] == mask
    assert sonoff_listener.attribute_updates[1][0] == relay_1_attr
    assert sonoff_listener.attribute_updates[1][1] is True
    assert sonoff_listener.attribute_updates[2][0] == relay_2_attr
    assert sonoff_listener.attribute_updates[2][1] is True


@pytest.mark.parametrize("quirk", (zhaquirks.sonoff.zbm5.zbm_3c_quirk,))
async def test_sonoff_zbm5_3c_cluster(zigpy_device_from_v2_quirk, quirk):
    """Test Sonoff ZBM5-3C custom cluster functionality."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={1: {0xFC11: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]
    sonoff_listener = ClusterListener(sonoff_cluster)

    # Test all three relays
    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = sonoff_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = sonoff_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = sonoff_cluster.AttributeDefs.relay_3_detached.id

    # Set all relays as detached
    mask = (
        zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
        | zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay2
        | zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay3
    )
    sonoff_cluster.update_attribute(detach_mask_attr, mask)

    # Should have updates for detach_mask and all three relay states
    assert len(sonoff_listener.attribute_updates) == 4
    assert sonoff_listener.attribute_updates[0][0] == detach_mask_attr
    assert sonoff_listener.attribute_updates[0][1] == mask
    assert sonoff_listener.attribute_updates[1][0] == relay_1_attr
    assert sonoff_listener.attribute_updates[1][1] is True
    assert sonoff_listener.attribute_updates[2][0] == relay_2_attr
    assert sonoff_listener.attribute_updates[2][1] is True
    assert sonoff_listener.attribute_updates[3][0] == relay_3_attr
    assert sonoff_listener.attribute_updates[3][1] is True


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test Sonoff cluster write_attributes logic without network calls."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]

    # Test the write_attributes method logic by calling it directly
    relay_1_attr = sonoff_cluster.AttributeDefs.relay_1_detached.name
    detach_mask_attr_id = sonoff_cluster.AttributeDefs.detach_relay_mask.id

    # Mock the parent class write_attributes call
    with mock.patch.object(
        sonoff_cluster.__class__.__bases__[0], "write_attributes"
    ) as mock_write:
        mock_write.return_value = None

        # Test writing relay_1_detached = True
        await sonoff_cluster.write_attributes({relay_1_attr: True})

        # Check that write_attributes was called with the converted mask
        mock_write.assert_called_once()
        # First argument is attributes dict
        call_args = mock_write.call_args[0][0]
        assert detach_mask_attr_id in call_args
        assert (
            call_args[detach_mask_attr_id]
            == zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1
        )
        # Should be removed from original attributes
        assert relay_1_attr not in call_args


async def test_sonoff_cluster_work_mode_enum(zigpy_device_from_v2_quirk):
    """Test Sonoff work mode enum values."""

    # Test enum values
    assert zhaquirks.sonoff.zbm5.SonoffWorkMode.EndDevice == 0x00
    assert zhaquirks.sonoff.zbm5.SonoffWorkMode.Router == 0x01

    # Test bitmap values
    assert zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay1 == 0b00000001
    assert zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay2 == 0b00000010
    assert zhaquirks.sonoff.zbm5.SonoffDetachedRelayMask.Relay3 == 0b00000100


async def test_sonoff_cluster_attribute_definitions(zigpy_device_from_v2_quirk):
    """Test Sonoff cluster attribute definitions."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={1: {0xFC11: "in"}},
    )

    sonoff_cluster = device.endpoints[1].in_clusters[0xFC11]

    # Test attribute IDs
    assert sonoff_cluster.AttributeDefs.work_mode.id == 0x0018
    assert sonoff_cluster.AttributeDefs.detach_relay_mask.id == 0x0019
    assert sonoff_cluster.AttributeDefs.relay_1_detached.id == 0x0FFA
    assert sonoff_cluster.AttributeDefs.relay_2_detached.id == 0x0FFB
    assert sonoff_cluster.AttributeDefs.relay_3_detached.id == 0x0FFC

    # Test cluster ID
    assert sonoff_cluster.cluster_id == 0xFC11
