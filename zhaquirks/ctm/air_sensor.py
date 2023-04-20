"""CTM Lyng Air Sensor"""
import zigpy.profiles.zha as zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Identify,
    Ota,
)
from zigpy.zcl.clusters.measurement import (
    TemperatureMeasurement,
    RelativeHumidity,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.ctm import CTM, CtmPowerConfiguration


class CtmLyngAirSensor(CustomDevice):
    """Custom device air sensor."""

    signature = {
        MODELS_INFO: [(CTM, "Air Sensor")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=770
            # device_version=1
            # input_clusters=[0, 1, 3, 1026, 1029]
            # output_clusters=[3, 25, 4096]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CtmPowerConfiguration,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }
