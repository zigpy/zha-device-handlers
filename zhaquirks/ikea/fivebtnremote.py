
"""Device handler for IKEA of Sweden TRADFRI remote control."""
import zigpy.types as t
from zigpy.profiles import zll
from zigpy.zcl.clusters.general import (
    Basic, Identify, Groups, Scenes, OnOff, LevelControl, PowerConfiguration,
    Alarms, Ota
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.quirks import CustomDevice
from . import LightLinkCluster
from .. import EventableCluster, DoublingPowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class ScenesCluster(EventableCluster, Scenes):
    """Ikea Scenes cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.server_commands.update({
            0x0007: ('press', (t.int8s, t.int8s, t.int8s, t.int8s), False),
            0x0008: ('hold', (t.int8s, t.int8s, t.int8s), False),
            0x0009: ('release', (t.int16s,), False)
        })


class IkeaTradfriRemote(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=49246 device_type=2096
        # device_version=2
        # input_clusters=[0, 1, 3, 9, 2821, 4096]
        # output_clusters=[3, 4, 5, 6, 8, 25, 4096]>
        'models_info': [
            ('IKEA of Sweden', 'TRADFRI remote control')
        ],
        'endpoints': {
            1: {
                'profile_id': zll.PROFILE_ID,
                'device_type': zll.DeviceType.SCENE_CONTROLLER,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    LightLink.cluster_id
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id
                ],
            },
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zll.PROFILE_ID,
                'device_type': zll.DeviceType.SCENE_CONTROLLER,
                'input_clusters': [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    LightLinkCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ScenesCluster,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id
                ],
            }
        },
    }
