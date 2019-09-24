"""Device handler for Yale Real Living."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import Alarms, Basic, Identify, Ota, PollControl, Time

from .. import DoublingPowerConfigurationCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class YaleRealLiving(CustomDevice):
    """Custom device representing Yale Real Living devices."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=10
        #  device_version=0
        #  input_clusters=[0, 1, 3, 9, 10, 257, 32]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [("Yale", "YRD210 PB DB"), ("Yale", "YRL220 TS LL")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Time.cluster_id,
                    DoorLock.cluster_id,
                    PollControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Time.cluster_id,
                    DoorLock.cluster_id,
                    PollControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [DoorLock.cluster_id, Ota.cluster_id],
            }
        }
    }
