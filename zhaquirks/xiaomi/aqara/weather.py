"""Xiaomi aqara weather sensor device."""
import logging

from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraTemperatureHumiditySensor
from zigpy.zcl.clusters.general import Groups, Identify
from zigpy.zcl.clusters.measurement import PressureMeasurement

from .. import (
    LUMI,
    BasicCluster,
    PowerConfigurationCluster,
    RelativeHumidityCluster,
    TemperatureMeasurementCluster,
    XiaomiCustomDevice,
)
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

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
        MODELS_INFO: [(LUMI, "lumi.weather")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: TEMPERATURE_HUMIDITY_DEVICE_TYPE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    TemperatureMeasurementCluster.cluster_id,
                    PressureMeasurement.cluster_id,
                    RelativeHumidityCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    TemperatureMeasurementCluster,
                    PressureMeasurement.cluster_id,
                    RelativeHumidityCluster,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        }
    }
