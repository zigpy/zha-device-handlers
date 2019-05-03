"""Device handler for centralite 3130."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Identify, LevelControl, OnOff, Ota, PollControl)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.centralite import PowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CentraLite3130(CustomDevice):
    """Custom device representing centralite 3130."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 2821]
        #  output_clusters=[3, 6, 8, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.LEVEL_CONTROL_SWITCH,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                DIAGNOSTICS_CLUSTER_ID
            ],
            'output_clusters': [
                Identify.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'CentraLite',
                'model': '3130',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id
                ],
            }
        },
    }
