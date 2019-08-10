"""Device handler for centralite 3157100."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Identify, Ota, Time, PollControl)
from zigpy.zcl.clusters.hvac import (
    Fan, Thermostat, UserInterface)

from zhaquirks.centralite import PowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CentraLite3157100(CustomDevice):
    """Custom device representing centralite 3157100."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=769
        #  device_version=0
        #  input_clusters=[0, 1, 3, 513, 514, 516, 32, 2821]
        #  output_clusters=[10, 25]>

        'models_info': [
            ('Centralite', '3157100')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.THERMOSTAT,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    Fan.cluster_id,
                    UserInterface.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
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
                'device_type': zha.DeviceType.THERMOSTAT,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    Fan.cluster_id,
                    UserInterface.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
                ],
                'output_clusters': [
                    Time.cluster_id,
                    Ota.cluster_id
                ],
            },
        },
    }
