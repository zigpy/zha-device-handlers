"""Device handler for centralite motion (only) sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.centralite import PowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
MANUFACTURER_SPECIFIC_PROFILE_ID = 0xC2DF  # decimal = 49887
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC46  # decimal = 64582


class CentraLiteMotionSensor(CustomDevice):
    """Custom device representing centralite motion (only) sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        #  output_clusters=[25]>
        #
        #  Supported models: 3325-S, 3326-L
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                IasZone.cluster_id,
                DIAGNOSTICS_CLUSTER_ID
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        },
        #  <SimpleDescriptor endpoint=2 profile=49887 device_type=263
        #  device_version=0
        #  input_clusters=[0, 1, 3, 2821, 64582]
        #  output_clusters=[3]>
        2: {
            'profile_id': MANUFACTURER_SPECIFIC_PROFILE_ID,
            'device_type': zha.DeviceType.OCCUPANCY_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                DIAGNOSTICS_CLUSTER_ID,
                MANUFACTURER_SPECIFIC_CLUSTER_ID
            ],
            'output_clusters': [
                Identify.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
            2: {
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id
                ],
            }
        },
    }
