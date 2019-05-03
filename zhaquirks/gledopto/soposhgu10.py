"""GLEDOPTO Soposh Dual White and color 5W GU10 300lm device."""
from zigpy.profiles import zll
from zigpy.profiles.zll import DeviceType
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Scenes)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink


class SoposhGU10(CustomDevice):
    """GLEDOPTO Soposh Dual White and color 5W GU10 300lm."""

    signature = {
        11: {
            'profile_id': zll.PROFILE_ID,
            'device_type': DeviceType.EXTENDED_COLOR_LIGHT,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Color.cluster_id
            ],
            'output_clusters': [
            ],
        },
        13: {
            'profile_id': zll.PROFILE_ID,
            'device_type': DeviceType.EXTENDED_COLOR_LIGHT,
            'input_clusters': [
                LightLink.cluster_id
            ],
            'output_clusters': [
                LightLink.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            11: {
                'profile_id': zll.PROFILE_ID,
                'device_type': DeviceType.EXTENDED_COLOR_LIGHT,
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id
                ],
                'output_clusters': [
                ],
            }
        },
    }
