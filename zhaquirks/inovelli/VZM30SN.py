"""VZM30-SN Smart On/Off Switch."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM30SNCluster

(
    QuirkBuilder("Inovelli", "VZM30-SN")
    .replace_cluster_occurrences(InovelliVZM30SNCluster)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
