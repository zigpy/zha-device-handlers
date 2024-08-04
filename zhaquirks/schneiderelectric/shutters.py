"""Quirks for Schneider Electric shutters."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SEBasic,
    SESpecific,
    SEWindowCovering,
)


class OneGangShutter1(CustomDevice):
    """1GANG/SHUTTER/1 from Schneider Electric."""

    signature = {
        MODELS_INFO: [
            (SE_MANUF_NAME, "1GANG/SHUTTER/1"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=5, profile=260, device_type=514,
            # device_version=0,
            # input_clusters=[0, 3, 4, 5, 258, 2821],
            # output_clusters=[25]>
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=21, profile=260, device_type=260,
            # device_version=0,
            # input_clusters=[0, 3, 2821, 65303],
            # output_clusters=[3, 5, 6, 8, 25, 258]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Diagnostic.cluster_id,
                    SESpecific.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    SEBasic,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    SEWindowCovering,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    SEBasic,
                    Identify.cluster_id,
                    Diagnostic.cluster_id,
                    SESpecific,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    SEWindowCovering,
                ],
            },
        }
    }
