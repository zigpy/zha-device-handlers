"""Philips RWL022 device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic

from zhaquirks.philips import SIGNIFY, PhilipsBasicCluster, PhilipsRwlRemoteCluster

DEVICE_SPECIFIC_UNKNOWN = 64512


(
    QuirkBuilder(SIGNIFY, "RWL022")
    .replaces(PhilipsBasicCluster, Basic.cluster_id, endpoint_id=1)
    .replaces(PhilipsRwlRemoteCluster, DEVICE_SPECIFIC_UNKNOWN, endpoint_id=1)
    .device_automation_triggers(
        PhilipsRwlRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
