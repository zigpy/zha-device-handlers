"""Philips RWL022 device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.philips import SIGNIFY, PhilipsBasicCluster, PhilipsRwlRemoteCluster

(
    QuirkBuilder(SIGNIFY, "RWL022")
    .replaces(PhilipsBasicCluster, endpoint_id=1)
    .replaces(PhilipsRwlRemoteCluster, endpoint_id=1)
    .device_automation_triggers(
        PhilipsRwlRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
