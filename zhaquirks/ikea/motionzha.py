"""Device handler for IKEA of Sweden TRADFRI remote control."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ikea import (
    IKEA,
    IKEA_CLUSTER_ID,
    LightLinkCluster,
    PowerConfiguration2CRCluster,
)


class IkeaTradfriMotion(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2128
        # device_version=2
        # input_clusters=[0, 1, 3, 9, 2821, 4096]
        # output_clusters=[3, 4, 6, 25, 4096]>
        MODELS_INFO: [(IKEA, "TRADFRI motion sensor")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration2CRCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    Diagnostic.cluster_id,
                    LightLinkCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }


class IkeaTradfriMotionE1745(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI motion sensor E1745."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2128
        # device_version=1
        # input_clusters=[0, 1, 3, 9, 32, 4096, 64636]
        # output_clusters=[3, 4, 6, 8, 25, 4096]>
        MODELS_INFO: [(IKEA, "TRADFRI motion sensor")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration2CRCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    PollControl.cluster_id,
                    LightLinkCluster,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }
