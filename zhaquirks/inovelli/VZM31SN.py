"""VZM31-SN Two in One Switch/Dimmer Module."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM31SNCluster

(
    QuirkBuilder("Inovelli", "VZM31-SN")
    .replace_cluster_occurrences(InovelliVZM31SNCluster)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
