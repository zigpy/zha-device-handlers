"""Tests for NodOn pilot wire quirks."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

import zhaquirks
from zhaquirks.builder.metadata import PreventDefaultEntityCreationMetadata
from zhaquirks.nodon.pilot_wire import (
    NODON_PILOT_WIRE_CLUSTER_ID,
    AdeoPilotWireCluster,
    NodOnPilotWireCluster,
    adeo,
    nodon,
)

zhaquirks.setup()


@pytest.mark.parametrize("builder", [nodon, adeo])
def test_pilot_wire_on_off_entities_not_created(builder):
    """No default entity is created for the On/Off cluster.

    The On/Off cluster is a legacy fallback for controllers without pilot wire
    support. The firmware does not support start_up_on_off, so the start-up
    behavior select is hidden along with the switch.
    """
    assert (
        PreventDefaultEntityCreationMetadata(
            endpoint_id=1,
            cluster_id=OnOff.cluster_id,
            cluster_type=ClusterType.Server,
            unique_id_suffix=None,
            function=None,
        )
        in builder.disabled_default_entities
    )


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
