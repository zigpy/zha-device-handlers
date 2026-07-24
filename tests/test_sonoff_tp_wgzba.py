"""Tests for the SONOFF TP-WGZBA thermostat quirk."""

from types import SimpleNamespace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.sonoff.tp_wgzba import (
    SONOFF_PRIVATE_CLUSTER_ID,
    SonoffTPWGZBAPrivateCluster,
    SonoffTPWGZBAThermostatCluster,
    TPWGZBASystemMode,
)

zhaquirks.setup()


def test_tp_wgzba_replaces_clusters_and_exposes_entities(zigpy_device_from_v2_quirk):
    """Test the thermostat and private clusters plus representative entities."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    endpoint = device.endpoints[1]
    assert isinstance(endpoint.thermostat, SonoffTPWGZBAThermostatCluster)
    assert isinstance(endpoint.sonoff_private, SonoffTPWGZBAPrivateCluster)

    entry = DEVICE_REGISTRY.match_entry(device)
    metadata_suffixes = {
        metadata.resolved_unique_id_suffix
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    assert {
        "tp_wgzba_ui_system_mode",
        "device_work_mode",
        "weekly_schedule_ui_apply",
        "temporary_mode_ui_apply",
    } <= metadata_suffixes


def test_tp_wgzba_system_mode_mapping():
    """Test the device schedule/manual modes map to HA thermostat modes."""
    assert (
        SonoffTPWGZBAThermostatCluster._system_mode_to_ha(TPWGZBASystemMode.Schedule)
        == Thermostat.SystemMode.Heat
    )
    assert (
        SonoffTPWGZBAThermostatCluster._system_mode_to_device(
            Thermostat.SystemMode.Heat
        )
        == TPWGZBASystemMode.Manual
    )


async def test_tp_wgzba_failed_mode_write_does_not_update_cache(
    zigpy_device_from_v2_quirk,
):
    """Test failed device writes do not report or cache a successful mode change."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    thermostat_cluster = device.endpoints[1].thermostat
    private_cluster = device.endpoints[1].sonoff_private
    failure = [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.FAILURE,
                Thermostat.AttributeDefs.system_mode.id,
            )
        ]
    ]

    with mock.patch.object(
        thermostat_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=failure),
    ):
        result = await private_cluster.write_attributes(
            {
                private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.name: (
                    TPWGZBASystemMode.Manual
                )
            }
        )

    assert result == failure
    assert (
        private_cluster.get(private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.name)
        is None
    )


async def test_tp_wgzba_reads_real_system_mode_from_device(
    zigpy_device_from_v2_quirk,
):
    """Test mode reads use the raw thermostat value before the local fallback."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    thermostat_cluster = device.endpoints[1].thermostat
    private_cluster = device.endpoints[1].sonoff_private
    mode_attribute = Thermostat.AttributeDefs.system_mode
    record = foundation.ReadAttributeRecord(
        attrid=mode_attribute.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(
            type=mode_attribute.zcl_type,
            value=TPWGZBASystemMode.Manual,
        ),
    )

    with mock.patch.object(
        thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=([record],)),
    ):
        mode = await private_cluster._read_real_system_mode()

    assert mode == TPWGZBASystemMode.Manual


def test_tp_wgzba_schedule_response_updates_ui_values(zigpy_device_from_v2_quirk):
    """Test standard weekly schedule responses populate the UI cache."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    private_cluster = device.endpoints[1].sonoff_private
    response = SimpleNamespace(
        day_of_week_for_sequence=0x04,
        num_transitions_for_sequence=2,
        values=(
            SimpleNamespace(transition_time=30, heat_setpoint=2100),
            SimpleNamespace(transition_time=90, heat_setpoint=2300),
        ),
    )

    private_cluster._update_weekly_schedule_ui_from_rsp(response)

    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_day.name)
        == 2
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_time1.name)
        == 0
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_time2.name)
        == 90
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_temp1.name)
        == 2100
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_temp2.name)
        == 2300
    )


def test_tp_wgzba_schedule_rejects_non_contiguous_slots(zigpy_device_from_v2_quirk):
    """Test a non-NULL schedule slot cannot follow a NULL slot."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    private_cluster = device.endpoints[1].sonoff_private

    with pytest.raises(ValueError, match="after NULL"):
        private_cluster._validate_weekly_schedule_ui_updates(
            {
                private_cluster._WEEKLY_TIME_ATTRS[1].id: 0xFFFF,
                private_cluster._WEEKLY_TIME_ATTRS[2].id: 90,
            }
        )


async def test_tp_wgzba_weekly_schedule_command_encoding(
    zigpy_device_from_v2_quirk,
):
    """Test weekly schedule writes encode day, mode, and temperature values."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    thermostat_cluster = device.endpoints[1].thermostat

    with mock.patch.object(
        thermostat_cluster, "command", mock.AsyncMock(return_value="sent")
    ) as command:
        result = await thermostat_cluster.set_weekly_schedule_heat(
            0x02, [(0, 20.0), (30, 21.0)]
        )

    assert result == "sent"
    command.assert_awaited_once_with(
        thermostat_cluster.ServerCommandDefs.set_weekly_schedule.id,
        2,
        thermostat_cluster.SeqDayOfWeek(0x02),
        thermostat_cluster.SeqMode.Heat,
        [0, 2000, 30, 2100],
        manufacturer=None,
        expect_reply=True,
        tsn=None,
    )


async def test_tp_wgzba_temporary_mode_ui_command(zigpy_device_from_v2_quirk):
    """Test the temporary mode UI command dispatches a boost request."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    private_cluster = device.endpoints[1].sonoff_private
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_action.id,
        1,
    )
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_duration_minutes.id,
        10,
    )

    with mock.patch.object(
        private_cluster, "set_boost", mock.AsyncMock(return_value="boosted")
    ) as set_boost:
        result = await private_cluster.command(
            private_cluster.ServerCommandDefs.temporary_mode_ui_apply.id
        )

    assert result == "boosted"
    set_boost.assert_awaited_once_with(600, 30.0)
