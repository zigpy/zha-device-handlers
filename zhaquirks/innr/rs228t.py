"""Innr RS 228 T device."""
from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, GreenPowerProxy, Groups, Identify, LevelControl, OnOff, Ota, Scenes)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink


class RS228T(CustomDevice):
    """Innr RS 228 T device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=268
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 8, 768, 4096]
        # output_clusters=[25]>
        1: {
            'manufacturer': 'innr',
            'model': 'RS 228 T',
            'profile_id': zha.PROFILE_ID,
            'device_type': 268,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Color.cluster_id,
                LightLink.cluster_id
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
        # device_version=0
        # input_clusters=[]
        # output_clusters=[33]>
        242: {
            'profile_id': 41440,
            'device_type': 97,
            'input_clusters': [
            ],
            'output_clusters': [
                GreenPowerProxy.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': DeviceType.COLOR_DIMMABLE_LIGHT,
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
            242: {
                'profile_id': 41440,
                'device_type': 97,
                'input_clusters': [
                ],
                'output_clusters': [
                    GreenPowerProxy.cluster_id
                ],
            },
        },
    }
