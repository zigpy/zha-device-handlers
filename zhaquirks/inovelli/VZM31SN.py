"""VZM31-SN Two in One Switch/Dimmer Module."""

from zigpy.quirks.v2 import add_to_registry_v2
from zigpy.zcl import ClusterType

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM31SNCluster

(
    add_to_registry_v2("Inovelli", "VZM31-SN")
    .replaces(InovelliVZM31SNCluster)
    .replaces(InovelliVZM31SNCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
)
