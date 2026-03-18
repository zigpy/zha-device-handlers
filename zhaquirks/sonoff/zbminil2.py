"""Sonoff ZBMINIL2 - No-Neutral Zigbee Switch."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic

from zhaquirks import LocalDataCluster


class BasicConfigCluster(LocalDataCluster, Basic):
    """Attributes override for basic config."""

    _CONSTANT_ATTRIBUTES = {
        Basic.AttributeDefs.power_source.id: Basic.PowerSource.Mains_single_phase,
    }


(
    QuirkBuilder("SONOFF", "ZBMINIL2")
    .replace_cluster_occurrences(BasicConfigCluster, replace_client_instances=False)
    .add_to_registry()
)
