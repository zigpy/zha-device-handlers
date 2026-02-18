"""Tests for Aqara Shutter Switch H2 EU (lumi.switch.aeu003) quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogInput, MultistateInput

from tests.common import ClusterListener


class _EventListener:
    def __init__(self):
        self.events = []

    def zha_send_event(self, action, args):
        self.events.append((action, args))


@pytest.mark.asyncio
async def test_position_percent_updates_cover(zigpy_device_from_v2_quirk):
    """Position percent should update cover lift percentage (inverted)."""
    device = zigpy_device_from_v2_quirk(
        "Aqara",
        "lumi.switch.aeu003",
        endpoint_ids=[1, 2, 3, 4, 21],
        cluster_ids={
            1: {
                WindowCovering.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            2: {0xFCC0: ClusterType.Server},
            3: {
                MultistateInput.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            4: {
                MultistateInput.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            21: {AnalogInput.cluster_id: ClusterType.Server},
        },
    )

    manu_cluster = device.endpoints[1].opple_cluster
    cover_cluster = device.endpoints[1].window_covering
    cover_listener = ClusterListener(cover_cluster)

    manu_cluster._update_attribute(0x041F, 0)

    assert (WindowCovering.AttributeDefs.current_position_lift_percentage.id, 100) in (
        cover_listener.attribute_updates
    )


@pytest.mark.asyncio
async def test_position_stuck_after_stop_nudged(zigpy_device_from_v2_quirk):
    """If movement stops at an end, position is nudged to keep controls enabled."""
    device = zigpy_device_from_v2_quirk(
        "Aqara",
        "lumi.switch.aeu003",
        endpoint_ids=[1, 2, 3, 4, 21],
        cluster_ids={
            1: {
                WindowCovering.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            2: {0xFCC0: ClusterType.Server},
            3: {
                MultistateInput.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            4: {
                MultistateInput.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            21: {AnalogInput.cluster_id: ClusterType.Server},
        },
    )

    manu_cluster = device.endpoints[1].opple_cluster
    cover_cluster = device.endpoints[1].window_covering
    cover_listener = ClusterListener(cover_cluster)

    manu_cluster.read_attributes = mock.AsyncMock(return_value=([], []))

    manu_cluster._update_attribute(0x0420, 0)
    manu_cluster._update_attribute(0x041F, 0)

    assert (WindowCovering.AttributeDefs.current_position_lift_percentage.id, 50) in (
        cover_listener.attribute_updates
    )


@pytest.mark.asyncio
async def test_multistate_input_emits_event(zigpy_device_from_v2_quirk):
    """Multistate input updates should emit zha_send_event and update attr 0."""
    device = zigpy_device_from_v2_quirk(
        "Aqara",
        "lumi.switch.aeu003",
        endpoint_ids=[1, 2, 3, 4, 21],
        cluster_ids={
            1: {
                WindowCovering.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            2: {0xFCC0: ClusterType.Server},
            3: {
                MultistateInput.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            4: {
                MultistateInput.cluster_id: ClusterType.Server,
                0xFCC0: ClusterType.Server,
            },
            21: {AnalogInput.cluster_id: ClusterType.Server},
        },
    )

    multistate_cluster = device.endpoints[3].multistate_input
    listener = _EventListener()
    multistate_cluster.add_listener(listener)

    multistate_cluster._update_attribute(0x0055, 1)

    assert multistate_cluster._attr_cache.get(0) == "3_single"
    assert listener.events
