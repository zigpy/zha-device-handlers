"""Device handler for smartthings motionV4 sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, BinaryInput, Identify, Ota, PollControl)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.centralite import PowerConfigurationCluster


class SmartThingsMotionV4(CustomDevice):
    """SmartThingsMotionV4."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 15, 1026, 1280, 32]
        #  output_clusters=[25]>
        1: {
            'manufacturer': 'SmartThings',
            'model': 'motionv4',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                BinaryInput.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                IasZone.cluster_id,
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'SmartThings',
                'model': 'motionv4',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            }
        },
    }
