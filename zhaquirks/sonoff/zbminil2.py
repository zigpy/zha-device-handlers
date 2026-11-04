"""Sonoff ZBMINIL2 - Zigbee no-neutral switch."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive

from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("SONOFF", "ZBMINIL2")
    # The device reads the coordinator's KeepAlive server but does not advertise the
    # client side of the cluster. Unanswered reads make the device attempt a Trust
    # Center rejoin and eventually leave the network.
    .adds(KeepAlive, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
