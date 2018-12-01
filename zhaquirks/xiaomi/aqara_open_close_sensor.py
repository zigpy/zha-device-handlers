import logging

from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff,\
    PowerConfiguration, Identify
from zigpy import quirks
from zigpy.quirks.xiaomi import AqaraOpenCloseSensor
from zhaquirks.xiaomi import BasicCluster, PowerConfigurationCluster,\
    TemperatureMeasurementCluster, XiaomiCustomDevice

OPEN_CLOSE_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

#  remove the zigpy version of this device handler
if AqaraOpenCloseSensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraOpenCloseSensor)


class AqaraOpenCloseSensor(XiaomiCustomDevice):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        #  device_version=1
        #  input_clusters=[0, 3, 65535, 6]
        #  output_clusters=[0, 4, 65535]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OPEN_CLOSE_DEVICE_TYPE,
            'input_clusters': [
                BasicCluster.cluster_id,
                Identify.cluster_id,
                XIAOMI_CLUSTER_ID,
                OnOff.cluster_id
            ],
            'output_clusters': [
                BasicCluster.cluster_id,
                Groups.cluster_id,
                XIAOMI_CLUSTER_ID
            ],
        },
    }

    replacement = {
        'manufacturer': 'LUMI',
        'model': 'lumi.sensor_magnet.aq2',
        'endpoints': {
            1: {
                'input_clusters': [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster
                ],
                'output_clusters': [
                    BasicCluster,
                    Groups.cluster_id,
                    OnOff.cluster_id
                ],
            }
        },
    }
