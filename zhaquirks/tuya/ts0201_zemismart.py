"""Zemismart temp and humidity sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zdo.types import NodeDescriptor

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class ZemismartTempHumidity(CustomDevice):
    """Custom device representing Zemismart temp and humidity sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        # device_version=1
        # input_clusters=[0, 1, 3, 1029, 1026, 61183]
        # output_clusters=[3, 25]>
        MODELS_INFO: [("_TZ3000_lfa05ajd", "TS0201")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    0xEEFF,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02,
            0x40,
            0x80,
            0x1037,
            0x7F,
            0x0064,
            0x2C00,
            0x0064,
            0x00,  # Forcing capability 0x80 instead of 0x84 so AC Power = false
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    RelativeHumidity.cluster_id,
                    TemperatureMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
