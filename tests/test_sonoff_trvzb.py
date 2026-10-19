"""Tests for the Sonoff TRVZB / TRV-ZBT quirk."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.sonoff.trvzb import CustomSonoffCluster

zhaquirks.setup()


@pytest.mark.parametrize("model", ["TRVZB", "TRV-ZBT"])
async def test_sonoff_trvzb_quirk_applies(zigpy_device_from_v2_quirk, model):
    """The TRVZB quirk replaces the Sonoff 0xFC11 cluster on both model strings."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        model,
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                CustomSonoffCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    cluster = device.endpoints[1].in_clusters[CustomSonoffCluster.cluster_id]
    assert isinstance(cluster, CustomSonoffCluster)
    assert (
        cluster.AttributeDefs.external_temperature_sensor_value.id in cluster.attributes
    )
