"""Samjin Multi 2019 Refresh Quirk."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.samjin import SAMJIN
from zhaquirks.smartthings import SmartThingsAccelCluster

(
    QuirkBuilder(SAMJIN, "multi")
    .replaces(
        replacement_cluster_class=SmartThingsAccelCluster,
        cluster_id=SmartThingsAccelCluster.cluster_id,
        endpoint_id=1,
    )
    .add_to_registry()
)
