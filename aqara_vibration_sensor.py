import logging

from zigpy.quirks import CustomDevice
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, PowerConfiguration, \
    Identify, Ota, Scenes, MultistateInput
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.util import ListenableMixin
from xiaomi_common import BasicCluster, PowerConfigurationCluster

VIBE_DEVICE_TYPE = 0x5F02

_LOGGER = logging.getLogger(__name__)

PROFILES[zha.PROFILE_ID].CLUSTERS[zha.DeviceType.DOOR_LOCK] = (
    [
        Basic.cluster_id,
        PowerConfiguration.cluster_id,
        Identify.cluster_id,
        Ota.cluster_id,
        DoorLock.cluster_id
    ],
    [
        Basic.cluster_id,
        Identify.cluster_id,
        Groups.cluster_id,
        Scenes.cluster_id,
        Ota.cluster_id,
        DoorLock.cluster_id
    ])

PROFILES[zha.PROFILE_ID].CLUSTERS[VIBE_DEVICE_TYPE] = (
    [
        Identify.cluster_id,
        MultistateInput.cluster_id
    ],
    [
        Identify.cluster_id,
        Groups.cluster_id,
        Scenes.cluster_id,
        MultistateInput.cluster_id
    ])


class AqaraVibrationSensor(CustomDevice, ListenableMixin):
    _listeners = {}

    signature = {
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DOOR_LOCK,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                DoorLock.cluster_id
               ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id,
                DoorLock.cluster_id
                ],
        },
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': VIBE_DEVICE_TYPE,
            'input_clusters': [
                Identify.cluster_id,
                MultistateInput.cluster_id
               ],
            'output_clusters': [
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                MultistateInput.cluster_id
                ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    DoorLock.cluster_id
                    ],
            }
        },
    }
