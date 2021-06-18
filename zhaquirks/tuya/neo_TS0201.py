"""Neo Tuya Temperature, Humidity and Illumination Sensor."""

import zigpy
from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class NeoUnknownCluster(CustomCluster):
    """Neo Unknown Cluster (0xE002)"""

    name = "Neo Unknown Cluster"
    cluster_id = 0xE002


class TemperatureHumidtyIlluminanceSensor(CustomDevice):
    """Neo Tuya Temperature, Humidity and Illumination Sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        # Add missing endpoint 2
        sensor_endpoint = self.add_endpoint(2)
        sensor_endpoint.status = zigpy.endpoint.Status.ZDO_INIT
        sensor_endpoint.profile_id = zha.PROFILE_ID
        sensor_endpoint.device_type = DeviceType.TEMPERATURE_SENSOR
        sensor_endpoint.add_input_cluster(
            TemperatureMeasurement.cluster_id,
            TemperatureMeasurement(endpoint=sensor_endpoint, is_server=True),
        )
        sensor_endpoint.add_input_cluster(
            RelativeHumidity.cluster_id,
            RelativeHumidity(endpoint=sensor_endpoint, is_server=True),
        )

    signature = {
        #  <SimpleDescriptor endpoint=1, profile=260, device_type=262
        #  device_version=1
        #  input_clusters=[0, 1, 1024, 57346]
        #  output_clusters=[25, 10]>
        MODELS_INFO: [("_TZ3000_qaaysllp", "TS0201")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    NeoUnknownCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
