"""VZM35-SN Fan Switch."""

from zigpy.quirks.v2 import add_to_registry_v2
from zigpy.zcl import ClusterType

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM35SNCluster

(
    add_to_registry_v2("Inovelli", "VZM35-SN")
    .replaces(InovelliVZM35SNCluster)
    .replaces(InovelliVZM35SNCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
)
