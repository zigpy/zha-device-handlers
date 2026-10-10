"""Tests for Yoolax day/night shades."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya import TUYA_MCU_COMMAND
from zhaquirks.tuya.mcu import TuyaCoverControl
from zhaquirks.yoolax.cellular_daynightshade import (
    InvertedWindowCoveringCluster,
    YoolaxNewWindowCovering,
)

zhaquirks.setup()


async def test_yoolax_new_window_covering_commands(zigpy_device_from_v2_quirk):
    """Test command translations for newer Yoolax shades."""

    device = zigpy_device_from_v2_quirk("_TZE210_yqwse3h5", "TS0301")
    cover_cluster = device.endpoints[1].window_covering

    assert isinstance(cover_cluster, YoolaxNewWindowCovering)

    with mock.patch.object(
        device.command_bus,
        "listener_event",
    ) as listener_event:
        await cover_cluster.up_open()
        listener_event.assert_called_once()
        assert listener_event.call_args.args[0] == TUYA_MCU_COMMAND
        assert listener_event.call_args.args[1].cluster_attr == (
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        assert listener_event.call_args.args[1].attr_value == 0

    with mock.patch.object(
        device.command_bus,
        "listener_event",
    ) as listener_event:
        await cover_cluster.down_close()
        listener_event.assert_called_once()
        assert listener_event.call_args.args[0] == TUYA_MCU_COMMAND
        assert listener_event.call_args.args[1].cluster_attr == (
            WindowCovering.AttributeDefs.current_position_lift_percentage.name
        )
        assert listener_event.call_args.args[1].attr_value == 100

    with mock.patch.object(
        device.command_bus,
        "listener_event",
    ) as listener_event:
        await cover_cluster.stop()
        listener_event.assert_called_once()
        assert listener_event.call_args.args[0] == TUYA_MCU_COMMAND
        assert listener_event.call_args.args[1].cluster_attr == (
            cover_cluster.AttributeDefs.tuya_cover_command.name
        )
        assert listener_event.call_args.args[1].attr_value == TuyaCoverControl.Close


async def test_yoolax_legacy_window_covering_inversion(zigpy_device_from_v2_quirk):
    """Test conversion logic for older Yoolax shades."""

    device = zigpy_device_from_v2_quirk("_TZE200_eatmkx5j", "TS0301")
    cover_cluster = device.endpoints[1].window_covering

    assert isinstance(cover_cluster, InvertedWindowCoveringCluster)

    cluster_listener = ClusterListener(cover_cluster)
    cover_cluster.update_attribute(
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        25,
    )

    assert len(cluster_listener.attribute_updates) == 1
    assert cluster_listener.attribute_updates[0] == (
        WindowCovering.AttributeDefs.current_position_lift_percentage.id,
        75,
    )

    with mock.patch.object(
        cover_cluster,
        "request",
        mock.AsyncMock(return_value=(foundation.Status.SUCCESS, "done")),
    ) as request_mock:
        await cover_cluster.up_open()

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
        )
        assert request_mock.call_args[0][3] == 100

    with mock.patch.object(
        cover_cluster,
        "request",
        mock.AsyncMock(return_value=(foundation.Status.SUCCESS, "done")),
    ) as request_mock:
        await cover_cluster.down_close()

        assert request_mock.call_count == 1
        assert request_mock.call_args[0][1] == (
            WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
        )
        assert request_mock.call_args[0][3] == 0
