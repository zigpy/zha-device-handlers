"""Tradfri CCT light Quirk."""

from zigpy.profiles import zha, zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ikea import IKEA


class CCTLightZHA(CustomDevice):
    """TRADFRI CCT lights with ZHA profile but ZLL device type."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=544
        # device_version=2
        # input_clusters=[0, 3, 4, 5, 6, 8, 768, 2821, 4096]
        # output_clusters=[5, 25, 32, 4096]>
        MODELS_INFO: [
            (IKEA, "TRADFRI bulb GU10 WS 400lm"),
            (IKEA, "FLOALT panel WS 30x90"),
            (IKEA, "FLOALT panel WS 60x60"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }
