"""Device handler for Yale Real Living."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms, Basic, Identify, Ota, PollControl, Time)
from zigpy.zcl.clusters.closures import (
    DoorLock)

from zhaquirks import DoublingPowerConfigurationCluster


class YaleRealLiving(CustomDevice):
    """Custom device representing Yale Real Living devices."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=10
        #  device_version=0
        #  input_clusters=[0, 1, 3, 9, 10, 257, 32]
        #  output_clusters=[10, 25]>

        'models_info': [
            ('Yale', 'YRD210 PB DB'),
            ('Yale', 'YRL220 TS LL')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.DOOR_LOCK,
                'input_clusters': [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Time.cluster_id,
                    DoorLock.cluster_id,
                    PollControl.cluster_id
                ],
                'output_clusters': [
                    Time.cluster_id,
                    Ota.cluster_id
                ],
            },
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.DOOR_LOCK,
                'input_clusters': [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Time.cluster_id,
                    DoorLock.cluster_id,
                    PollControl.cluster_id
                ],
                'output_clusters': [
                    DoorLock.cluster_id,
                    Ota.cluster_id
                ],
            },
        }
    }
