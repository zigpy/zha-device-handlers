"""Device handler for centralite ias sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.centralite import PowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CentraLiteIASSensor(CustomDevice):
    """Custom device representing centralite ias sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        #  output_clusters=[25]>
        #
        #  Supported models: 3315-S, 3320-L
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
        #  <SimpleDescriptor endpoint=2 profile=49887 device_type=12
        #  device_version=0
        #  input_clusters=[0, 1, 3, 2821, 64527]
        #  output_clusters=[3]>
        2: {
            'profile_id': 49887,
            'device_type': 12,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                DIAGNOSTICS_CLUSTER_ID,
                64527
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
                    64527
                ],
                'output_clusters': [
                    Identify.cluster_id
                ],
            }
        },
    }
