"""Philips first generation RWL devices."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    PhilipsBasicCluster,
    PhilipsRwlRemoteCluster,
)

(
    QuirkBuilder(PHILIPS, "RWL020")
    .applies_to(SIGNIFY, "RWL020")
    .applies_to(PHILIPS, "RWL021")
    .applies_to(SIGNIFY, "RWL021")
    .replaces(PhilipsBasicCluster, endpoint_id=2)
    .replaces(PhilipsRwlRemoteCluster, endpoint_id=2)
    .device_automation_triggers(
        PhilipsRwlRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
