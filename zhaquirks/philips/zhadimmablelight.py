"""Quirk for Phillips dimmable bulbs."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    PhilipsLevelControlCluster,
    PhilipsOnOffCluster,
)


class ZHADimmableLight(CustomDevice):
    """Philips ZigBee HomeAutomation dimmable bulb device."""

    signature = {
        MODELS_INFO: [
            (PHILIPS, "LWA004"),
            (PHILIPS, "LWA005"),
            (PHILIPS, "LWA007"),
            (PHILIPS, "LWO001"),
            (PHILIPS, "LWO003"),
            (PHILIPS, "LWU001"),
            (PHILIPS, "LWV001"),
            (SIGNIFY, "LWA004"),
            (SIGNIFY, "LWA005"),
            (SIGNIFY, "LWA007"),
            (SIGNIFY, "LWO001"),
            (SIGNIFY, "LWO003"),
            (SIGNIFY, "LWU001"),
            (SIGNIFY, "LWV001"),
        ],
        ENDPOINTS: {
            11: {
                # <SimpleDescriptor endpoint=11 profile=260 device_type=528
                # device_version=2
                # input_clusters=[0, 3, 4, 5, 6, 8, 4096, 64514]
                # output_clusters=[25]
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    64514,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PhilipsOnOffCluster,
                    PhilipsLevelControlCluster,
                    LightLink.cluster_id,
                    64514,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
