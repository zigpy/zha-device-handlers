"""Device handler for IKEA of Sweden TRADFRI Fyrtur blinds."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ikea import IKEA, IKEA_CLUSTER_ID


class IkeaTradfriRollerBlinds(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI Fyrtur blinds."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=514
        # device_version=1
        # input_clusters=[0, 1, 3, 4, 5, 32, 258, 4096, 64636]
        # output_clusters=[25, 4096]>
        MODELS_INFO: [
            (IKEA, "FYRTUR block-out roller blind"),
            (IKEA, "KADRILJ roller blind"),
            (IKEA, "TREDANSEN block-out cellul blind"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PollControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, LightLink.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PollControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, LightLink.cluster_id],
            }
        }
    }


class IkeaTradfriRollerBlinds2(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI Fyrtur blinds."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=514
        # device_version=1
        # input_clusters=[0, 1, 3, 4, 5, 32, 258, 4096]
        # output_clusters=[25, 4096]>
        MODELS_INFO: [
            (IKEA, "FYRTUR block-out roller blind"),
            (IKEA, "KADRILJ roller blind"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PollControl.cluster_id,
                    WindowCovering.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, LightLink.cluster_id],
            }
        },
    }

    replacement = IkeaTradfriRollerBlinds.replacement
