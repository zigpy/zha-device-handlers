"""Tests for Tuya TS0301 covers with inverted lift percentages."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering

import zhaquirks
from zhaquirks.tuya.ts0301_cover import (
    ZemismartTS0301WindowCoveringCluster,
    _invert_lift_percentage,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("device_position", "zcl_position"),
    [(0, 100), (25, 75), (50, 50), (75, 25), (100, 0)],
)
def test_ts0301_position_report(
    zigpy_device_from_v2_quirk, device_position, zcl_position
):
    """Device percentages are inverted before ZHA reads the attribute."""
    device = zigpy_device_from_v2_quirk(
        "_TZE200_cirjrpxe",
        "TS0301",
        cluster_ids={1: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cover = device.endpoints[1].window_covering
    assert isinstance(cover, ZemismartTS0301WindowCoveringCluster)

    cover._update_attribute(
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        device_position,
    )
    assert (
        cover.get(WindowCovering.AttributeDefs.current_position_lift_percentage.name)
        == zcl_position
    )


def test_ts0301_tilt_is_not_modified(zigpy_device_from_v2_quirk):
    """The quirk changes lift values only, not unrelated attributes."""
    device = zigpy_device_from_v2_quirk(
        "_TZE200_cirjrpxe",
        "TS0301",
        cluster_ids={1: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cover = device.endpoints[1].window_covering
    cover._update_attribute(
        WindowCovering.AttributeDefs.current_position_tilt_percentage.id, 25
    )
    assert (
        cover.get(WindowCovering.AttributeDefs.current_position_tilt_percentage.name)
        == 25
    )


@pytest.mark.parametrize("value", [None, -1, 101, True])
def test_ts0301_unknown_positions_pass_through(value):
    """Do not transform unknown or invalid lift values."""
    assert _invert_lift_percentage(value) == value


@pytest.mark.parametrize(
    ("zcl_position", "device_position"),
    [(0, 100), (25, 75), (50, 50), (75, 25), (100, 0)],
)
async def test_ts0301_go_to_lift_percentage(
    zigpy_device_from_v2_quirk, zcl_position, device_position
):
    """Outgoing ZCL position targets are inverted for the device."""
    device = zigpy_device_from_v2_quirk(
        "_TZE200_cirjrpxe",
        "TS0301",
        cluster_ids={1: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cover = device.endpoints[1].window_covering

    with mock.patch.object(
        cover.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        await cover.command(
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id, zcl_position
        )

    request_mock.assert_called_once()
    assert request_mock.call_args.kwargs["data"][-1] == device_position


@pytest.mark.parametrize(
    ("zcl_position", "device_position"),
    [(0, 100), (25, 75), (50, 50), (75, 25), (100, 0)],
)
async def test_ts0301_keyword_go_to_lift_percentage(
    zigpy_device_from_v2_quirk, zcl_position, device_position
):
    """Keyword lift position targets are inverted before sending."""
    device = zigpy_device_from_v2_quirk(
        "_TZE200_cirjrpxe",
        "TS0301",
        cluster_ids={1: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cover = device.endpoints[1].window_covering

    with mock.patch.object(
        cover.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        await cover.command(
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id,
            percentage_lift_value=zcl_position,
        )

    request_mock.assert_called_once()
    assert request_mock.call_args.kwargs["data"][-1] == device_position


@pytest.mark.parametrize(
    "command_id",
    [
        WindowCovering.ServerCommandDefs.up_open.id,
        WindowCovering.ServerCommandDefs.down_close.id,
        WindowCovering.ServerCommandDefs.stop.id,
    ],
)
async def test_ts0301_open_close_stop_unchanged(zigpy_device_from_v2_quirk, command_id):
    """Open, close, and stop commands retain their standard ZCL IDs."""
    device = zigpy_device_from_v2_quirk(
        "_TZE200_cirjrpxe",
        "TS0301",
        cluster_ids={1: {WindowCovering.cluster_id: ClusterType.Server}},
    )
    cover = device.endpoints[1].window_covering

    with mock.patch.object(
        cover.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        await cover.command(command_id)

    request_mock.assert_called_once()
    assert request_mock.call_args.kwargs["data"][-1] == command_id
