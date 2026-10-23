"""Tests for NodOn pilot wire quirks."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

import zhaquirks
from zhaquirks.nodon.pilot_wire import (
    NODON_PILOT_WIRE_CLUSTER_ID,
    AdeoPilotWireCluster,
    NodOnPilotWireCluster,
    adeo,
    nodon,
)

zhaquirks.setup()


@pytest.mark.parametrize("builder", [nodon, adeo])
def test_pilot_wire_only_on_off_switch_hidden(builder):
    """Only the On/Off switch is hidden, not the start-up behavior select."""

    class Switch:
        pass

    class StartupOnOffSelectEntity:
        pass

    metas = [
        meta
        for meta in builder.disabled_default_entities
        if meta.endpoint_id == 1
        and meta.cluster_id == OnOff.cluster_id
        and meta.cluster_type == ClusterType.Server
    ]
    assert len(metas) == 1
    assert metas[0].function(Switch())
    assert not metas[0].function(StartupOnOffSelectEntity())


@pytest.mark.parametrize(
    ("manufacturer", "model", "expected_cluster"),
    [
        ("NodOn", "SIN-4-FP-21", NodOnPilotWireCluster),
        ("Adeo", "SIN-4-FP-21_EQU", AdeoPilotWireCluster),
    ],
)
def test_pilot_wire_quirk_applied(
    zigpy_device_from_v2_quirk, manufacturer, model, expected_cluster
):
    """The quirk replaces the pilot wire cluster on NodOn and Adeo devices."""
    device = zigpy_device_from_v2_quirk(
        manufacturer,
        model,
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                NODON_PILOT_WIRE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    ep = device.endpoints[1]
    assert isinstance(ep.in_clusters[NODON_PILOT_WIRE_CLUSTER_ID], expected_cluster)
