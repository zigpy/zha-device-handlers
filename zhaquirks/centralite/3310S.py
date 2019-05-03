"""Centralite 3310S implementation."""
from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.smartthings import (
    SmartthingsRelativeHumidityCluster, SmartthingsTemperatureHumiditySensor)
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.centralite import PowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


#  remove the zigpy version of this device handler
if SmartthingsTemperatureHumiditySensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(SmartthingsTemperatureHumiditySensor)


class CentraLite3310S(CustomDevice):
    """CentraLite3310S custom device implementation."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 2821, 64581]
        #  output_clusters=[3, 25]>

        1: {
            'manufacturer': 'CentraLite',
            'model': '3310-S',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.TEMPERATURE_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                DIAGNOSTICS_CLUSTER_ID,
                SmartthingsRelativeHumidityCluster.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'CentraLite',
                'model': '3310-S',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    SmartthingsRelativeHumidityCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Ota.cluster_id
                ],
            }
        },
    }
