"""Knockoff ORVIBO motion sensors.

Aka. ZHONGXING. Based on Orvibo motion sensor code.
"""

from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, Groups, PowerConfiguration, Scenes

from zhaquirks import Bus, PowerConfigurationCluster
from zhaquirks.zhongxing import ZHONGXING, MotionCluster


class SN10ZW(CustomDeviceV2):
    """SN10ZW motion sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(ZHONGXING, "700ae5aab3414ec09c1872efe7b8755a")
    .device_class(SN10ZW)
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(MotionCluster, endpoint_id=1)
    .adds(Basic.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(PowerConfiguration.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(Groups.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(Scenes.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
