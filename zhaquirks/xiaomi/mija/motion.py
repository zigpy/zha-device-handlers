"""Xiaomi mija body sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    MotionCluster,
    OccupancyCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)

XIAOMI_CLUSTER_ID = 0xFFFF
_LOGGER = logging.getLogger(__name__)


class Motion(XiaomiQuickInitDevice):
    """Custom device representing mija body sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=263
        #  device_version=1
        #  input_clusters=[0, 65535, 3, 25]
        #  output_clusters=[0, 3, 4, 5, 6, 8, 25]>
        MODELS_INFO: [(LUMI, "lumi.sensor_motion")],
        NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    Ota.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Ota.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    OccupancyCluster,
                    MotionCluster,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }
