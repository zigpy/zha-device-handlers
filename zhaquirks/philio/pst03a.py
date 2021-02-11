"""Device handler for Philio PST03A-v2.2.5."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Alarms,
    OnOff,
    BinaryInput,
    Ota,
)
from zigpy.zcl.clusters.measurement import (
    TemperatureMeasurement,
    IlluminanceMeasurement,
    OccupancySensing,
)
from zigpy.zcl.clusters.security import IasZone
from . import PHILIO, MotionCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    MANUFACTURER,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)


class Pst03a(CustomDevice):
    """Custom device representing PST03A 4in1 motion/opening/temperature/illuminance sensors."""

    signature = {
        MODEL: "PST03A-v2.2.5",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Alarms.cluster_id,
                    OccupancySensing.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Alarms.cluster_id,
                    BinaryInput.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        MANUFACTURER: PHILIO,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Alarms.cluster_id,
                    MotionCluster,
                    TemperatureMeasurement.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Alarms.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
