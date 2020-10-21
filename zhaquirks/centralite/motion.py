"""Device handler for centralite motion (only) sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import CENTRALITE
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC46  # decimal = 64582
MANUFACTURER_SPECIFIC_PROFILE_ID = 0xC2DF  # decimal = 49887


class CentraLiteMotionSensor(CustomDevice):
    """Custom device representing centralite motion (only) sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: [
            (CENTRALITE, "3305-S"),
            (CENTRALITE, "3325-S"),
            (CENTRALITE, "3326-L"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            #  <SimpleDescriptor endpoint=2 profile=49887 device_type=263
            #  device_version=0
            #  input_clusters=[0, 1, 3, 2821, 64582]
            #  output_clusters=[3]>
            2: {
                PROFILE_ID: MANUFACTURER_SPECIFIC_PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }
