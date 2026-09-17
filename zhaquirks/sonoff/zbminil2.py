"""Sonoff ZBMINIL2 - Zigbee no-neutral switch."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive

(
    QuirkBuilder("SONOFF", "ZBMINIL2")
    # The device reads the coordinator's Keep-Alive server but does not advertise the
    # client side of the cluster, so the reads are otherwise ignored. Unanswered reads
    # make the device attempt a Trust Center rejoin and eventually leave the network.
    .adds(KeepAlive, cluster_type=ClusterType.Client)
    .add_to_registry()
)
