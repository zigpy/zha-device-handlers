"""Tests for the SONOFF TP-WGZBA thermostat quirk."""

from unittest import mock

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
