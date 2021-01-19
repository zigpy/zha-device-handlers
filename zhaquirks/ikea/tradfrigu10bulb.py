"""Tradfri GU10 bulb Quirk."""
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

from . import IKEA


class TradfriGU10Bulb(CustomDevice):
    """TRADFRI GU10 WS 400lm."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=544
        # device_version=2
        # input_clusters=[0, 3, 4, 5, 6, 8, 768, 2821, 4096]
        # output_clusters=[5, 25, 32, 4096]>
        "models_info": [(IKEA, "TRADFRI bulb GU10 WS 400lm")],
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zll.DeviceType.COLOR_TEMPERATURE_LIGHT,
                "input_clusters": [
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
                "output_clusters": [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
        "manufacturer": IKEA,
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                "input_clusters": [
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
                "output_clusters": [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }
