"""Device handler for Terncy awareness switch."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)

from zhaquirks import DoublingPowerConfigurationCluster

from . import (
    BUTTON_TRIGGERS,
    IlluminanceMeasurementCluster,
    MotionClusterLeft,
    MotionClusterRight,
    OccupancyCluster,
    TemperatureMeasurementCluster,
    TerncyRawCluster,
)
from .. import Bus
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

TERNCY_AWARENESS_DEVICE_TYPE = 0x01F0


class TerncyAwarenessSwitch(CustomDevice):
    """Terncy awareness switch."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_left_bus = Bus()
        self.motion_right_bus = Bus()
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=496
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1024, 1026, 1030, 64716]
        #  output_clusters=[25]>
        MODELS_INFO: [("Xiaoyan", "TERNCY-PP01"), (None, "TERNCY-PP01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: TERNCY_AWARENESS_DEVICE_TYPE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    OccupancySensing.cluster_id,
                    TerncyRawCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: TERNCY_AWARENESS_DEVICE_TYPE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IlluminanceMeasurementCluster,
                    TemperatureMeasurementCluster,
                    MotionClusterLeft,
                    OccupancyCluster,
                    TerncyRawCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: TERNCY_AWARENESS_DEVICE_TYPE,
                INPUT_CLUSTERS: [MotionClusterRight],
                OUTPUT_CLUSTERS: [],
            },
        }
    }

    device_automation_triggers = BUTTON_TRIGGERS
