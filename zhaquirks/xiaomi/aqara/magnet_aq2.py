"""Xiaomi aqara contact sensor device."""
import logging

from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraOpenCloseSensor
from zigpy.zcl.clusters.general import Groups, Identify, OnOff

from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

OPEN_CLOSE_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

#  remove the zigpy version of this device handler
if AqaraOpenCloseSensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraOpenCloseSensor)


class MagnetAQ2(XiaomiCustomDevice):
    """Xiaomi contact sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        #  device_version=1
        #  input_clusters=[0, 3, 65535, 6]
        #  output_clusters=[0, 4, 65535]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_magnet.aq2',
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
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_magnet.aq2',
                'input_clusters': [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    XIAOMI_CLUSTER_ID
                ],
                'output_clusters': [
                    BasicCluster,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    XIAOMI_CLUSTER_ID
                ],
            }
        },
    }
