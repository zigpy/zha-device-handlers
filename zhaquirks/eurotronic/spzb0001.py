"""Eurotronic Spirit Zigbee quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType

from zhaquirks.eurotronic import EUROTRONIC, ThermostatCluster

(
    QuirkBuilder(EUROTRONIC, "SPZB0001")
    .replaces(ThermostatCluster, cluster_type=ClusterType.Server, endpoint_id=1)
    .replaces(ThermostatCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
