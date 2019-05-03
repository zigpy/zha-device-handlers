"""Xiaomi aqara leak sensor device."""
from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraWaterSensor
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

#  remove the zigpy version of this device handler
if AqaraWaterSensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraWaterSensor)


class LeakAQ1(XiaomiCustomDevice):
    """Xiaomi aqara leak sensor device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=1
        #  input_clusters=[0, 3, 1]
        #  output_clusters=[25]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_wleak.aq1',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'input_clusters': [
                BasicCluster.cluster_id,
                Identify.cluster_id,
                PowerConfigurationCluster.cluster_id,
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_wleak.aq1',
                'input_clusters': [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    IasZone.cluster_id
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            }
        },
    }
