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
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,  # 0x0202
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    WindowCovering.cluster_id,  # 0x0102
                    Diagnostic.cluster_id,  # 0x0B05
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],  # 0x0019
            },
            # <SimpleDescriptor endpoint=21, profile=260, device_type=260,
            # device_version=0,
            # input_clusters=[0, 3, 2821, 65303],
            # output_clusters=[3, 5, 6, 8, 25, 258]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,  # 0x0104
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Diagnostic.cluster_id,  # 0x0B05
                    SESpecific.cluster_id,  # 0xFF17
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Ota.cluster_id,  # 0x0019
                    WindowCovering.cluster_id,  # 0x0102
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,  # 0x0202
                INPUT_CLUSTERS: [
                    SEBasic,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    SEWindowCovering,  # 0x0102
                    Diagnostic.cluster_id,  # 0x0B05
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],  # 0x0019
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,  # 0x0104
                INPUT_CLUSTERS: [
                    SEBasic,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Diagnostic.cluster_id,  # 0x0B05
                    SESpecific,  # 0xff17
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Ota.cluster_id,  # 0x0019
                    SEWindowCovering,  # 0x0102
                ],
            },
        }
    }
