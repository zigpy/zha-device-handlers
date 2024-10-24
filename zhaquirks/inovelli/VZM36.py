"""VZM36 Canopy Module."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType

from zhaquirks.inovelli import (
    INOVELLI_AUTOMATION_TRIGGERS,
    InovelliVZM36FanCluster,
    InovelliVZM36LightCluster,
)

(
    QuirkBuilder("Inovelli", "VZM36")
    .replaces(InovelliVZM36LightCluster)
    .replaces(InovelliVZM36FanCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
