"""Osram A19 tunable white device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Ota, Scenes)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lighting import Color

from . import OsramLightCluster


class A19TunableWhite(CustomDevice):
    """Osram A19 tunable white device."""

    signature = {
        # <SimpleDescriptor endpoint=3 profile=260 device_type=258
        # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 768, 64527]
        # output_clusters=[25]>
        'models_info': [
            ('OSRAM', 'LIGHTIFY A19 Tunable White')
        ],
        3: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.COLOR_DIMMABLE_LIGHT,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Color.cluster_id,
                ElectricalMeasurement.cluster_id,
                OsramLightCluster.cluster_id
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        }
    }

    replacement = {
        'endpoints': {
            3: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    OsramLightCluster
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
        }
    }
