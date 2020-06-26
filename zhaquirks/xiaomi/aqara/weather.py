"""Xiaomi aqara weather sensor device."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Groups, Identify
from zigpy.zcl.clusters.measurement import PressureMeasurement

from .. import (
    LUMI,
    BasicCluster,
    PowerConfigurationCluster,
    PressureMeasurementCluster,
    RelativeHumidityCluster,
    TemperatureMeasurementCluster,
    XiaomiCustomDevice,
)
from ... import Bus
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)

TEMPERATURE_HUMIDITY_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)


class Weather(XiaomiCustomDevice):
    """Xiaomi weather sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.temperature_bus = Bus()
        self.humidity_bus = Bus()
        self.pressure_bus = Bus()
        super().__init__(*args, **kwargs)

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
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    TemperatureMeasurementCluster,
                    PressureMeasurementCluster,
                    RelativeHumidityCluster,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        },
    }


class Weather2(Weather):
    """New Xiaomi weather sensor device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        #  device_version=1
        #  input_clusters=[0, 3, 65535, 1026, 1027, 1029]
        #  output_clusters=[0, 4, 65535]>
        MODELS_INFO: [(LUMI, "lumi.weather")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurementCluster.cluster_id,
                    PressureMeasurement.cluster_id,
                    RelativeHumidityCluster.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        },
    }
