
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Identify,\
    PollControl, Ota, BinaryInput
from quirks.centralite import PowerConfigurationCluster
from zigpy.quirks import CustomDevice


DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class SmartThingsTagV4(CustomDevice):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=12 device_version=0 input_clusters=[0, 1, 3, 15, 32] output_clusters=[3, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.SIMPLE_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                BinaryInput.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Ota.cluster_id
            ],
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    BinaryInput.cluster_id
                ]
            }
        },
    }
