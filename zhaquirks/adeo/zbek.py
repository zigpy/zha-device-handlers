"""Quirk for Adeo ZBEK-1 and ZBEK-4 bulbs."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive

from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("Adeo", "ZBEK-1")
    .applies_to("Adeo", "ZBEK-4")
    # These bulbs read KeepAlive attributes from the coordinator but may omit
    # the client cluster from their endpoint descriptor.
    .adds(KeepAlive.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
