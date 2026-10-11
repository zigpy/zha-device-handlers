"""Tests for the Sonoff SNZT-03P quirk."""

from types import SimpleNamespace

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.measurement import OccupancySensing

import zhaquirks
from zhaquirks.sonoff.snzt03p import SonoffPrivateCluster

zhaquirks.setup()


@pytest.mark.parametrize("model", ["SNZT-03P", "SNZB-03PR2"])
async def test_sonoff_snzt03p_matching(zigpy_device_from_v2_quirk, model):
    """Both supported models receive the private cluster replacement."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model=model,
        cluster_ids={
            1: {
                OccupancySensing.cluster_id: ClusterType.Server,
                SonoffPrivateCluster.cluster_id: ClusterType.Server,
            }
        },
    )
    assert isinstance(device.endpoints[1].sonoff_private, SonoffPrivateCluster)


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        (SimpleNamespace(translation_key="pir_o_to_u_delay"), True),
        (SimpleNamespace(translation_key="occupancy"), False),
        (SimpleNamespace(), False),
    ],
)
def test_sonoff_snzt03p_default_entity_filter(entity, expected):
    """Hide the duplicate delay control without hiding unrelated entities."""
    entry = next(
        entry
        for entry in DEVICE_REGISTRY
        if entry.source.module == "zhaquirks.sonoff.snzt03p"
    )
    (rule,) = entry.zha_device_factory.quirk_definition.disabled_default_entities
    assert rule.function(entity) is expected
