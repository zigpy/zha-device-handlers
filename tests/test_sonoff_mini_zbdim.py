"""Tests for Sonoff MINI-ZBDIM quirks."""

import importlib
from unittest import mock

from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl

from tests.common import ClusterListener
import zhaquirks

mini_zbdim = importlib.import_module("zhaquirks.sonoff.mini-zbdim")
SonoffCluster = mini_zbdim.SonoffCluster
SonoffLevelControl = mini_zbdim.SonoffLevelControl

zhaquirks.setup()


async def test_sonoff_mini_zbdim_write_attributes_maps_virtual_actions(
    zigpy_device_from_v2_quirk,
):
    """Virtual calibration action attributes should map to the real device attribute."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]

    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        start_value = bytes([0x01, 0x01, 0x01]).decode("latin-1")
        await sonoff_cluster.write_attributes(
            {SonoffCluster.AttributeDefs.set_calibration_action_start.name: start_value}
        )

        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1
        assert (
            written_attrs[0].attrid
            == SonoffCluster.AttributeDefs.set_calibration_action.id
        )
        assert written_attrs[0].value.value == start_value

        stop_value = bytes([0x01, 0x01, 0x02]).decode("latin-1")
        await sonoff_cluster.write_attributes(
            {
                SonoffCluster.AttributeDefs.set_calibration_action_stop.name: stop_value,
                SonoffCluster.AttributeDefs.delayed_power_on_state.name: True,
            }
        )

        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 2
        assert (
            written_attrs[0].attrid
            == SonoffCluster.AttributeDefs.set_calibration_action.id
        )
        assert written_attrs[0].value.value == stop_value
        assert (
            written_attrs[1].attrid
            == SonoffCluster.AttributeDefs.delayed_power_on_state.id
        )
        assert written_attrs[1].value.value is True


async def test_sonoff_mini_zbdim_apply_custom_configuration_reads_backed_attributes(
    zigpy_device_from_v2_quirk,
):
    """Pairing configuration should read the attributes behind exposed entities."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        sonoff_cluster,
        "read_attributes",
        mock.AsyncMock(),
    ) as mock_read:
        await sonoff_cluster.apply_custom_configuration()

    mock_read.assert_awaited_once_with(
        [
            SonoffCluster.AttributeDefs.delayed_power_on_state.id,
            SonoffCluster.AttributeDefs.delayed_power_on_time.id,
            SonoffCluster.AttributeDefs.external_trigger_mode.id,
            SonoffCluster.AttributeDefs.calibration_status.id,
            SonoffCluster.AttributeDefs.calibration_progress.id,
            SonoffCluster.AttributeDefs.transition_time.id,
            SonoffCluster.AttributeDefs.min_brightness_threshold.id,
            SonoffCluster.AttributeDefs.dimming_light_rate.id,
            SonoffCluster.AttributeDefs.max_brightness_threshold.id,
            SonoffCluster.AttributeDefs.level_for_calibration.id,
        ]
    )


async def test_sonoff_mini_zbdim_level_control_clamps_minimum_level(
    zigpy_device_from_v2_quirk,
):
    """Current level values below the device minimum should be clamped to 2."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBDIM",
        cluster_ids={
            1: {
                LevelControl.cluster_id: ClusterType.Server,
            }
        },
    )

    level_cluster = device.endpoints[1].level
    listener = ClusterListener(level_cluster)
    current_level_id = SonoffLevelControl.AttributeDefs.current_level.id

    level_cluster.update_attribute(current_level_id, 1)
    assert listener.attribute_updates[-1] == (current_level_id, 2)
    assert level_cluster.get(current_level_id) == 2

    level_cluster.update_attribute(current_level_id, 3)
    assert listener.attribute_updates[-1] == (current_level_id, 3)
    assert level_cluster.get(current_level_id) == 3
