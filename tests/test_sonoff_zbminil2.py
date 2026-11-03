"""Tests for the SONOFF ZBMINIL2 device."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff as OnOffCluster

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.zbminil2 import (
    SonoffCluster,
    SonoffExternalSwitchTriggerType,
)

zhaquirks.setup()

# the quirk replaces the Sonoff cluster on endpoint 1 only
DEVICE_CLUSTERS = {
    1: {
        OnOffCluster.cluster_id: ClusterType.Server,
        SonoffCluster.cluster_id: ClusterType.Server,
    },
}

EXTERNAL_TRIGGER_MODE_ATTR_ID = SonoffCluster.AttributeDefs.external_trigger_mode.id


def test_zbminil2_cluster_replacement(zigpy_device_from_v2_quirk):
    """The custom Sonoff cluster is installed on the device."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "ZBMINIL2", cluster_ids=DEVICE_CLUSTERS
    )

    cluster = device.endpoints[1].in_clusters[SonoffCluster.cluster_id]
    assert isinstance(cluster, SonoffCluster)


def test_zbminil2_external_trigger_mode_attribute_definition():
    """The external trigger mode attribute is defined on the custom cluster."""
    attr_def = SonoffCluster.AttributeDefs.external_trigger_mode
    assert attr_def.id == EXTERNAL_TRIGGER_MODE_ATTR_ID == 0x0016
    assert attr_def.type is SonoffExternalSwitchTriggerType


@pytest.mark.parametrize(
    ("member", "raw_value", "name"),
    [
        (SonoffExternalSwitchTriggerType.Edge_trigger, 0x00, "Edge_trigger"),
        (SonoffExternalSwitchTriggerType.Pulse_trigger, 0x01, "Pulse_trigger"),
    ],
    ids=["edge", "pulse"],
)
def test_zbminil2_external_trigger_mode_enum(member, raw_value, name):
    """The external trigger mode enum exposes the expected members."""
    assert member.value == raw_value
    assert member.name == name
    assert SonoffExternalSwitchTriggerType(raw_value) == member


def test_zbminil2_external_trigger_mode_unknown_value():
    """Unknown trigger mode values fall back to a pseudo member."""
    unknown = SonoffExternalSwitchTriggerType(0x99)
    assert unknown.name == "undefined_0x99"


@pytest.mark.parametrize(
    "trigger_mode",
    [
        SonoffExternalSwitchTriggerType.Edge_trigger,
        SonoffExternalSwitchTriggerType.Pulse_trigger,
    ],
    ids=["edge", "pulse"],
)
def test_zbminil2_external_trigger_mode_update(
    zigpy_device_from_v2_quirk, trigger_mode
):
    """Updating the external trigger mode attribute reports the new value."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF", "ZBMINIL2", cluster_ids=DEVICE_CLUSTERS
    )

    cluster = device.endpoints[1].in_clusters[SonoffCluster.cluster_id]
    attribute_listener = ClusterListener(cluster)

    cluster.update_attribute(EXTERNAL_TRIGGER_MODE_ATTR_ID, trigger_mode)

    assert attribute_listener.attribute_updates == [
        (EXTERNAL_TRIGGER_MODE_ATTR_ID, trigger_mode)
    ]
    assert cluster.get(EXTERNAL_TRIGGER_MODE_ATTR_ID) == trigger_mode