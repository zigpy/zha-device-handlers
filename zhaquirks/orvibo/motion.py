"""ORVIBO motion sensors.

Based on Konke motion sensor code.
"""

from typing import Any

from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, PowerConfigurationCluster
from zhaquirks.orvibo import ORVIBO_LATIN, MotionCluster, OccupancyCluster

ORVIBO_CLUSTER_ID = 0xFFFF


class OrviboMotionDevice(CustomDeviceV2):
    """Custom device class for ORVIBO motion sensors that need occupancy_bus."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(ORVIBO_LATIN, "895a2d80097f4ae2b2d40500d5e03dcc")
    .device_class(OrviboMotionDevice)
    .replaces(
        PowerConfigurationCluster,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=1,
    )
    .replaces(MotionCluster, cluster_id=IasZone.cluster_id, endpoint_id=1)
    .removes(ORVIBO_CLUSTER_ID, endpoint_id=1)
    .adds(OccupancyCluster, endpoint_id=1)
    .add_to_registry()
)
