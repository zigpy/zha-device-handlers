"""Tests for Aqara Shutter Switch H2 EU (lumi.switch.aeu003) quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import AnalogInput, MultistateInput

from tests.common import ClusterListener
from zhaquirks.xiaomi.aqara.switch_aeu003 import InvertedWindowCoveringCluster


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


@pytest.mark.parametrize(
    ("device_reports", "expected_in_ha"),
    [
        (0, 100),
        (100, 0),
        (20, 80),
        (80, 20),
        (50, 50),
    ],
)
async def test_window_covering_position_inversion(
    zigpy_device_from_v2_quirk, device_reports, expected_in_ha
):
    """WindowCovering position reports should be inverted for ZHA."""
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

    cluster = device.endpoints[1].window_covering
    assert isinstance(cluster, InvertedWindowCoveringCluster)
    listener = ClusterListener(cluster)

    cluster._update_attribute(
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        device_reports,
    )

    assert listener.attribute_updates == [
        (
            WindowCovering.AttributeDefs.current_position_lift_percentage.id,
            expected_in_ha,
        )
    ]


@pytest.mark.parametrize(
    ("zha_sends", "device_should_receive"),
    [
        (0, 100),
        (100, 0),
        (20, 80),
        (80, 20),
        (50, 50),
    ],
)
async def test_go_to_lift_percentage_command_inverted(
    zigpy_device_from_v2_quirk, zha_sends, device_should_receive
):
    """Outgoing go_to_lift_percentage commands should be inverted."""
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

    cluster = device.endpoints[1].window_covering
    assert isinstance(cluster, InvertedWindowCoveringCluster)
    command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id

    with mock.patch.object(
        WindowCovering, "request", new_callable=mock.AsyncMock
    ) as base_request:
        base_request.return_value = foundation.Status.SUCCESS, "done"

        await cluster.request(False, command_id, {}, zha_sends)

        base_request.assert_called_once()
        assert base_request.call_args.args[3] == device_should_receive


async def test_non_position_commands_unchanged(zigpy_device_from_v2_quirk):
    """Commands other than go_to_lift_percentage should pass through."""
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

    cluster = device.endpoints[1].window_covering
    stop_command_id = WindowCovering.ServerCommandDefs.stop.id

    with mock.patch.object(
        WindowCovering, "request", new_callable=mock.AsyncMock
    ) as base_request:
        base_request.return_value = foundation.Status.SUCCESS, "done"

        await cluster.request(False, stop_command_id, {})

        base_request.assert_called_once()
        assert base_request.call_args.args[1] == stop_command_id
