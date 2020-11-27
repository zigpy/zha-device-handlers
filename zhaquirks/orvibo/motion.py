"""ORVIBO motion sensors.

Based on Konke motion sensor code.
"""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.security import IasZone

from . import ORVIBO_LATIN, MotionCluster, OccupancyCluster
from .. import Bus, PowerConfigurationCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

ORVIBO_CLUSTER_ID = 0xFFFF


class SN10ZW(CustomDevice):
    """SN10ZW motion sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=1
        #  input_clusters=[0, 1, 3, 1280, 65535]
        #  output_clusters=[0, 1, 3, 4, 5]>
        MODELS_INFO: [(ORVIBO_LATIN, "895a2d80097f4ae2b2d40500d5e03dcc")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    ORVIBO_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    OccupancyCluster,
                    MotionCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
            }
        }
    }
