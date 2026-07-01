"""VZM32-SN MMwave Switch/Dimmer Module."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM32SNCluster

(
    QuirkBuilder("Inovelli", "VZM32-SN")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replace_cluster_occurrences(InovelliVZM32SNCluster)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
