import logging
import homeassistant.components.zha.const as zha_const
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, PowerConfiguration
from zhaquirks.xiaomi import BasicCluster, PowerConfigurationCluster,\
    TemperatureMeasurementCluster, XiaomiCustomDevice
from zhaquirks import EventableCluster

BUTTON_DEVICE_TYPE = 0x5F01
BUTTON_DEVICE_TYPE_REPLACEMENT = 0x6FF1
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

PROFILES[zha.PROFILE_ID].CLUSTERS[BUTTON_DEVICE_TYPE_REPLACEMENT] = (
    [
        BasicCluster.cluster_id,
        OnOff.cluster_id
    ],
    [
        BasicCluster.cluster_id,
        Groups.cluster_id
    ]
)

zha_const.DEVICE_CLASS[zha.PROFILE_ID].update(
    {
        BUTTON_DEVICE_TYPE_REPLACEMENT: 'sensor'
    }
)


class AqaraButton(XiaomiCustomDevice):

    class EventableOnOffCluster(EventableCluster, OnOff):
        cluster_id = OnOff.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 6, 65535]
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
        'manufacturer': 'LUMI',
        'model': 'lumi.sensor_switch.aq2',
        'endpoints': {
            1: {
                'device_type': BUTTON_DEVICE_TYPE_REPLACEMENT,
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    EventableOnOffCluster
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID
                ],
            }
        },
    }
