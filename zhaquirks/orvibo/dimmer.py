"""ORVIBO dimmers."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, LevelControl, OnOff, Scenes
from zigpy.zcl.clusters.lighting import Color

from . import ORVIBO
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class T10D1ZW(CustomDevice):
    """T10D1ZW in-wall dimmer."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1
        # device_version=0
        # input_clusters=[0, 4, 5, 6, 8, 768]
        # output_clusters=[0]>
        MODELS_INFO: [(ORVIBO, "abb71ca5fe1846f185cfbda554046cce")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LEVEL_CONTROL_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            }
        }
    }
