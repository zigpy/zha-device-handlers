"""Xiaomi aqara body sensor."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing

from .. import (
    LUMI,
    BasicCluster,
    IlluminanceMeasurementCluster,
    MotionCluster,
    OccupancyCluster,
    PowerConfigurationCluster,
    XiaomiCustomDevice,
)
from ... import Bus
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)

XIAOMI_CLUSTER_ID = 0xFFFF


class MotionAQ2(XiaomiCustomDevice):
    """Custom device representing aqara body sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        self.motion_bus = Bus()
        self.illuminance_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=260
        #  device_version=1
        #  input_clusters=[0, 65535, 1030, 1024]
        #  output_clusters=[0, 25]>
        MODELS_INFO: [(LUMI, "lumi.sensor_motion.aq2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    OccupancySensing.cluster_id,
                    IlluminanceMeasurementCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    IlluminanceMeasurementCluster,
                    OccupancyCluster,
                    MotionCluster,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id],
            }
        },
    }
