from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Identify,\
    PollControl, Ota, Commissioning
from zigpy.zcl.clusters.security import IasZone
from zhaquirks.centralite import PowerConfigurationCluster
from zigpy.quirks import CustomDevice


DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class Z308E3ED(CustomDevice):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 21, 1280, 32, 2821]
        #  output_clusters=[]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                IasZone.cluster_id,
                Commissioning.cluster_id,
                DIAGNOSTICS_CLUSTER_ID
            ],
            'output_clusters': [
            ],
        }
    }

    replacement = {
        'manufacturer': 'netvox',
        'model': 'Z308E3ED',
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Commissioning.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID
                ]
            }
        },
    }
