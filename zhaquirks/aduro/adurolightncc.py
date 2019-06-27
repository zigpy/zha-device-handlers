"""ADUROLIGHT Adurolight_NCC device."""
from zigpy.profiles import zha
from zigpy.profiles.zha import DeviceType
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff
)
from zigpy.zcl.clusters.lightlink import LightLink


ADUROLIGHT_CLUSTER_ID = 64716


class AdurolightNCC(CustomDevice):
    """ADUROLIGHT Adurolight_NCC device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2080
        # device_version=2
        # input_clusters=[0, 3, 8, 4096, 64716]
        # output_clusters=[3, 4, 6, 8, 4096, 64716]>
        'models_info': [
            ('ADUROLIGHT', 'Adurolight_NCC')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': DeviceType.NON_COLOR_CONTROLLER,
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    ADUROLIGHT_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    ADUROLIGHT_CLUSTER_ID
                ],
            }
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': DeviceType.NON_COLOR_CONTROLLER,
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    LightLink.cluster_id,
                    ADUROLIGHT_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    ADUROLIGHT_CLUSTER_ID
                ],
            }
        },
    }
