"""Device handler for Yale Real Living."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import Time

from zhaquirks import DoublingPowerConfigurationCluster

(
    QuirkBuilder("Yale", "YRD210 PB DB")
    .applies_to("Yale", "YRL220 TS LL")
    .applies_to("Yale", "YRD220/240 TSDB")
    .replaces(DoublingPowerConfigurationCluster, endpoint_id=1)
    .removes(Time.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(DoorLock.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
