"""Device handler for Lutron LZL4BWHL01 Remote."""
from zigpy.profiles import zll
from zigpy.zcl.clusters.general import Basic, Identify, Groups, Scenes, OnOff,\
    LevelControl
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.quirks import CustomDevice
from zhaquirks import GroupBoundCluster


MANUFACTURER_SPECIFIC_CLUSTER_ID_1 = 0xFF00  # decimal = 65280
MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC44  # decimal = 64580


class OnOffGroupCluster(GroupBoundCluster, OnOff):
    """On/Off Cluster which only binds to a group."""

    pass


class LevelControlGroupCluster(GroupBoundCluster, LevelControl):
    """Level Control Cluster which only binds to a group."""

    pass


class LutronLZL4BWHL01Remote(CustomDevice):
    """Custom device representing Lutron LZL4BWHL01 Remote."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2080
        #  device_version=2
        #  input_clusters=[0, 4096, 65280, 64580]
        #  output_clusters=[4096, 3, 6, 8, 4, 5, 0, 65280]>
        'models_info': [
            ('Lutron', 'LZL4BWHL01 Remote')
        ],
        'endpoints': {
            1: {
                'profile_id': zll.PROFILE_ID,
                'device_type': zll.DeviceType.CONTROLLER,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2
                ],
                'output_clusters': [
                    LightLink.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1
                ],
            },
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zll.PROFILE_ID,
                'device_type': zll.DeviceType.CONTROLLER,
                'input_clusters': [
                    Basic.cluster_id,
                    LightLink.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2
                ],
                'output_clusters': [
                    LightLink.cluster_id,
                    Identify.cluster_id,
                    OnOffGroupCluster,
                    LevelControlGroupCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_1
                ],
            }
        },
    }


class LutronLZL4BWHL01Remote2(LutronLZL4BWHL01Remote):
    """Custom device representing Lutron LZL4BWHL01 Remote."""

    signature = {
        'endpoints': {
            1: {
                **LutronLZL4BWHL01Remote.signature['endpoints'][1],
                'manufacturer': ' Lutron',  # Some remotes report this
            }
        }
    }
