"""Knockoff ORVIBO motion sensors.

Aka. ZHONGXING. Based on Orvibo motion sensor code.
"""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, Groups, PowerConfiguration, Scenes

from zhaquirks import PowerConfigurationCluster
from zhaquirks.zhongxing import ZHONGXING, MotionCluster

(
    QuirkBuilder(ZHONGXING, "700ae5aab3414ec09c1872efe7b8755a")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(MotionCluster, endpoint_id=1)
    .adds(Basic.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(PowerConfiguration.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(Groups.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(Scenes.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
