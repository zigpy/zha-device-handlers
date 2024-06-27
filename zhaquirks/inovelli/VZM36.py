"""VZM36 Canopy Module."""

from zigpy.quirks.v2 import add_to_registry_v2
from zigpy.zcl import ClusterType

from zhaquirks.inovelli import (
    INOVELLI_AUTOMATION_TRIGGERS,
    InovelliVZM36FanCluster,
    InovelliVZM36LightCluster,
)

(
    add_to_registry_v2("Inovelli", "VZM36")
    .replaces(InovelliVZM36LightCluster)
    .replaces(InovelliVZM36FanCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
)
