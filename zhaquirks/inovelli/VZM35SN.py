"""VZM35-SN Fan Switch."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType

from zhaquirks.inovelli import INOVELLI_AUTOMATION_TRIGGERS, InovelliVZM35SNCluster

(
    QuirkBuilder("Inovelli", "VZM35-SN")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replace_cluster_occurrences(InovelliVZM35SNCluster)
    # ep 3 is missing in zigpy DB for devices paired with an old fw version, add it:
    .replaces_endpoint(3, device_type=zha.DeviceType.DIMMER_SWITCH)
    # these missing clusters are needed for button presses to generate events:
    .replaces(InovelliVZM35SNCluster, endpoint_id=2, cluster_type=ClusterType.Client)
    .replaces(InovelliVZM35SNCluster, endpoint_id=3, cluster_type=ClusterType.Client)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
