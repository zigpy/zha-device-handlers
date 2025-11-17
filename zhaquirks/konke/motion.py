"""Konke motion sensor."""

from typing import Any

from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, PowerConfigurationCluster
from zhaquirks.konke import KONKE, MotionCluster, OccupancyCluster


class KonkeMotionDevice(CustomDeviceV2):
    """Custom device class for Konke motion sensors that need occupancy_bus."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(KONKE, "3AFE28010402000D")
    .applies_to(KONKE, "3AFE14010402000D")
    .applies_to(KONKE, "3AFE27010402000D")
    .device_class(KonkeMotionDevice)
    .replaces(
        PowerConfigurationCluster,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=1,
    )
    .replaces(MotionCluster, cluster_id=IasZone.cluster_id, endpoint_id=1)
    .adds(OccupancyCluster, endpoint_id=1)
    .add_to_registry()
)
