"""VZM35-SN Fan Switch."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM35SNCluster

(
    QuirkBuilder("Inovelli", "VZM35-SN")
    .replace_cluster_occurrences(InovelliVZM35SNCluster)
    .replaces(InovelliVZM35SNCluster, endpoint_id=2)
    .replaces(InovelliVZM35SNCluster, endpoint_id=3)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
