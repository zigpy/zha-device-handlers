"""Xiaomi aqara weather sensor device."""
import logging

from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraTemperatureHumiditySensor
from zigpy.zcl.clusters.general import Groups, Identify
from zigpy.zcl.clusters.measurement import (
    PressureMeasurement, RelativeHumidity, TemperatureMeasurement)

from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice)

TEMPERATURE_HUMIDITY_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

#  remove the zigpy version of this device handler
if AqaraTemperatureHumiditySensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraTemperatureHumiditySensor)


class Weather(XiaomiCustomDevice):
    """Xiaomi weather sensor device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        #  device_version=1
        #  input_clusters=[0, 3, 65535, 1026, 1027, 1029]
        #  output_clusters=[0, 4, 65535]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.weather',
            'profile_id': zha.PROFILE_ID,
            'device_type': TEMPERATURE_HUMIDITY_DEVICE_TYPE,
            'input_clusters': [
                BasicCluster.cluster_id,
                Identify.cluster_id,
                XIAOMI_CLUSTER_ID,
                TemperatureMeasurement.cluster_id,
                PressureMeasurement.cluster_id,
                RelativeHumidity.cluster_id
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
                'model': 'lumi.weather',
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    PressureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    XIAOMI_CLUSTER_ID
                ],
                'output_clusters': [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID
                ],
            }
        },
    }
