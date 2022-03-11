"""Quirk for Philips motion sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
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
from zhaquirks.philips import SIGNIFY, OccupancyCluster


class SignifyMotion(CustomDevice):
    """Philips motion sensor device."""

    signature = {
        MODELS_INFO: [(SIGNIFY, "SML003")],
        ENDPOINTS: {
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    OccupancyCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        }
    }
