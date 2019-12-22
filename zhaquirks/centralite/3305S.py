"""Device handler for centralite 3305."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import OccupancySensing, TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CentraLite3305S(CustomDevice):
    """Custom device representing centralite 3305."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: [
            (CENTRALITE, "3305-S"),
            (CENTRALITE, "3305"),
            (CENTRALITE, "3325-S"),
            (CENTRALITE, "3325"),
            (CENTRALITE, "3326-L"),
            (CENTRALITE, "3326"),
            (CENTRALITE, "3328-G"),
            (CENTRALITE, "Motion Sensor-A"),
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
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=263
            #  device_version=0
            #  input_clusters=[0, 1, 3, 1030, 2821]
            #  output_clusters=[3]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
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
                    OccupancySensing.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }


class CentraLite3305S2(CentraLite3305S):
    """Custom device representing centralite 3305 with one endpoint."""

    signature = {
        MODELS_INFO: [(CENTRALITE, "3305")],
        ENDPOINTS: {1: {**CentraLite3305S.signature["endpoints"][1]}},
    }

    replacement = {ENDPOINTS: {1: {**CentraLite3305S.replacement["endpoints"][1]}}}
