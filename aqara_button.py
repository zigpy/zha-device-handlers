import logging

from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, PowerConfiguration
from xiaomi_common import BasicCluster, PowerConfigurationCluster,\
    TemperatureMeasurementCluster, XiaomiCustomDevice

BUTTON_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

PROFILES[zha.PROFILE_ID].CLUSTERS[BUTTON_DEVICE_TYPE] = (
    [
        BasicCluster.cluster_id,
        PowerConfigurationCluster.cluster_id,
        TemperatureMeasurementCluster.cluster_id,
        OnOff.cluster_id
    ],
    [
        BasicCluster.cluster_id,
        Groups.cluster_id
    ]
)


class AqaraButton(XiaomiCustomDevice):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1 input_clusters=[0, 6, 65535]
        # output_clusters=[0, 4, 65535]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': BUTTON_DEVICE_TYPE,
            'input_clusters': [
                Basic.cluster_id,
                OnOff.cluster_id,
                XIAOMI_CLUSTER_ID
            ],
            'output_clusters': [
                Basic.cluster_id,
                Groups.cluster_id,
                XIAOMI_CLUSTER_ID
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    OnOff.cluster_id
                ],
            }
        },
    }
