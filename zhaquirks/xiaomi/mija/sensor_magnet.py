"""Xiaomi aqara contact sensor device."""
import logging

from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraOpenCloseSensor
from zigpy.zcl.clusters.general import (
    Groups, Identify, LevelControl, OnOff, Ota, Scenes)

from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

OPEN_CLOSE_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

#  remove the zigpy version of this device handler
if AqaraOpenCloseSensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraOpenCloseSensor)


class Magnet(XiaomiCustomDevice):
    """Xiaomi mija contact sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=260
        #  device_version=1
        #  input_clusters=[0, 3, 65535, 25]
        #  output_clusters=[0, 4, 3, 6, 8, 5, 25]>

        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_magnet',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DIMMER_SWITCH,
            'input_clusters': [
                BasicCluster.cluster_id,
                Identify.cluster_id,
                XIAOMI_CLUSTER_ID,
                Ota.cluster_id
            ],
            'output_clusters': [
                BasicCluster.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_magnet',
                'device_type': zha.DeviceType.REMOTE_CONTROL,
                'input_clusters': [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    XIAOMI_CLUSTER_ID,
                    Ota.cluster_id,
                ],
                'output_clusters': [
                    BasicCluster,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id
                ],
            }
        },
    }
