"""Osram Lightify X4 device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Ota, PollControl,
    PowerConfiguration, Scenes)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

OSRAM_DEVICE = 0x0810  # 2064 base 10
OSRAM_CLUSTER = 0xFD00  # 64768 base 10


_LOGGER = logging.getLogger(__name__)


class LightifyX4(CustomDevice):
    """Osram Lightify X4 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2064
        #  device_version=2
        #  input_clusters=[0, 1, 32, 4096, 64768]
        #  output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OSRAM_DEVICE,
            'model': 'Switch 4x-LIGHTIFY',
            'manufacturer': 'OSRAM',
            'input_clusters': [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                PollControl.cluster_id,
                LightLink.cluster_id,
                OSRAM_CLUSTER,
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Ota.cluster_id,
                Color.cluster_id,
                LevelControl.cluster_id,
                LightLink.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
        # device_version=2
        # input_clusters=[0, 4096, 64768]
        # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OSRAM_DEVICE,
            'input_clusters': [
                Basic.cluster_id,
                LightLink.cluster_id,
                OSRAM_CLUSTER
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Color.cluster_id,
                LevelControl.cluster_id,
                LightLink.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=3 profile=260 device_type=2064
        # device_version=2
        # input_clusters=[0, 4096, 64768]
        # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
        3: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OSRAM_DEVICE,
            'input_clusters': [
                Basic.cluster_id,
                LightLink.cluster_id,
                OSRAM_CLUSTER
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Color.cluster_id,
                LevelControl.cluster_id,
                LightLink.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=4 profile=260 device_type=2064
        # device_version=2
        # input_clusters=[0, 4096, 64768]
        # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
        4: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OSRAM_DEVICE,
            'input_clusters': [
                Basic.cluster_id,
                LightLink.cluster_id,
                OSRAM_CLUSTER
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Color.cluster_id,
                LevelControl.cluster_id,
                LightLink.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=5 profile=260 device_type=2064
        # device_version=2
        # input_clusters=[0, 4096, 64768]
        # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
        5: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OSRAM_DEVICE,
            'input_clusters': [
                Basic.cluster_id,
                LightLink.cluster_id,
                OSRAM_CLUSTER
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Color.cluster_id,
                LevelControl.cluster_id,
                LightLink.cluster_id
            ],
        },
        # <SimpleDescriptor endpoint=6 profile=260 device_type=2064
        # device_version=2
        # input_clusters=[0, 4096, 64768]
        # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
        6: {
            'profile_id': zha.PROFILE_ID,
            'device_type': OSRAM_DEVICE,
            'input_clusters': [
                Basic.cluster_id,
                LightLink.cluster_id,
                OSRAM_CLUSTER
            ],
            'output_clusters': [
                Groups.cluster_id,
                Identify.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                Color.cluster_id,
                LevelControl.cluster_id,
                LightLink.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'model': 'Switch 4x-LIGHTIFY',
                'manufacturer': 'OSRAM',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER,
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            2: {
                'model': 'Switch 4x-LIGHTIFY',
                'manufacturer': 'OSRAM',
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            3: {
                'model': 'Switch 4x-LIGHTIFY',
                'manufacturer': 'OSRAM',
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            4: {
                'model': 'Switch 4x-LIGHTIFY',
                'manufacturer': 'OSRAM',
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            5: {
                'model': 'Switch 4x-LIGHTIFY',
                'manufacturer': 'OSRAM',
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
            6: {
                'model': 'Switch 4x-LIGHTIFY',
                'manufacturer': 'OSRAM',
                'profile_id': zha.PROFILE_ID,
                'device_type': OSRAM_DEVICE,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER
                ],
                'output_clusters': [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Color.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id
                ],
            },
        }
    }
