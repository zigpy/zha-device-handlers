"""GLEDOPTO GL-S-007Z device."""
from zigpy.profiles import zha, zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Scenes)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink


class GLS007Z(CustomDevice):
    """GLEDOPTO GL-S-007Z device."""

    signature = {
        # <SimpleDescriptor endpoint=12 profile=260 device_type=258
        # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 768]
        # output_clusters=[]>
        12: {
            'manufacturer': 'GLEDOPTO',
            'model': 'GL-S-007Z',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.COLOR_DIMMABLE_LIGHT,
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
        # <SimpleDescriptor endpoint=11 profile=49246 device_type=528
        # device_version=2
        # input_clusters=[0, 3, 4, 5, 6, 8, 768]
        # output_clusters=[]>
        11: {
            'profile_id': zll.PROFILE_ID,
            'device_type': zll.DeviceType.EXTENDED_COLOR_LIGHT,
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
        # <SimpleDescriptor endpoint=13 profile=49246 device_type=57694
        # device_version=2
        # input_clusters=[4096]
        # output_clusters=[4096]>
        13: {
            'profile_id': zll.PROFILE_ID,
            'device_type': 57694,
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
            12: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.COLOR_DIMMABLE_LIGHT,
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
        }
    }
