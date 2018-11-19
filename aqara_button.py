import logging

from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, PowerConfiguration
from zigpy.util import ListenableMixin
from xiaomi_common import BasicCluster, PowerConfigurationCluster

BUTTON_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)

# This registers a device that Xiaomi didn't follow the spec on.
# Translated: For device type: 0x5F01 in the ZHA zigbee profile
# the input clusters are: [0x0000, 0x0006, 0xFFFF] and the output
# clusters are: [0x0000, 0x0004, 0xFFFF]. The goal is to read this
# from a configuration file in the future
PROFILES[zha.PROFILE_ID].CLUSTERS[BUTTON_DEVICE_TYPE] = (
    [Basic.cluster_id, OnOff.cluster_id, XIAOMI_CLUSTER_ID],
    [Basic.cluster_id, Groups.cluster_id, XIAOMI_CLUSTER_ID]
    )


class AqaraButton(CustomDevice, ListenableMixin):
    _listeners = {}

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1 input_clusters=[0, 6, 65535]
        # output_clusters=[0, 4, 65535]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': BUTTON_DEVICE_TYPE,
            'input_clusters': [
                Basic.cluster_id,
                OnOff.cluster_id,
                XIAOMI_CLUSTER_ID
               ],
            'output_clusters': [
                Basic.cluster_id,
                Groups.cluster_id,
                XIAOMI_CLUSTER_ID
                ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    OnOff.cluster_id,
                    XIAOMI_CLUSTER_ID
                    ],
            }
        },
    }
