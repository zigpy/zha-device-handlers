"""ADEO / Lexman ZBEK smart bulbs."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive

from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("Adeo", "ZBEK-1")
    .applies_to("Adeo", "ZBEK-4")
    .applies_to("Adeo", "ZBEK-13")
    # ADEO devices report the manufacturer as "Adeo" or "ADEO" (the ZBEK-26
    # remote uses "ADEO"). Only "Adeo" is confirmed for ZBEK-1, so match both.
    .applies_to("ADEO", "ZBEK-1")
    .applies_to("ADEO", "ZBEK-4")
    .applies_to("ADEO", "ZBEK-13")
    # The bulbs read the coordinator's KeepAlive server but do not advertise the
    # client side of the cluster. Unanswered reads make them do a Trust Center
    # rejoin seconds later, and they can end up dropping off the network.
    .adds(KeepAlive, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
