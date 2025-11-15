"""Philips first generation RWL devices."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic

from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    PhilipsBasicCluster,
    PhilipsRwlRemoteCluster,
)

DEVICE_SPECIFIC_UNKNOWN = 64512

(
    QuirkBuilder(PHILIPS, "RWL020")
    .applies_to(SIGNIFY, "RWL020")
    .applies_to(PHILIPS, "RWL021")
    .applies_to(SIGNIFY, "RWL021")
    .replaces(PhilipsBasicCluster, cluster_id=Basic.cluster_id, endpoint_id=2)
    .replaces(
        PhilipsRwlRemoteCluster, cluster_id=DEVICE_SPECIFIC_UNKNOWN, endpoint_id=2
    )
    .device_automation_triggers(
        PhilipsRwlRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
