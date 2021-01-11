"""Quirk for Phillips extended color bulbs."""
from zigpy.profiles import zll
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
from zigpy.zcl.clusters.lighting import Color
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
    PhilipsColorCluster,
    PhilipsLevelControlCluster,
    PhilipsOnOffCluster,
)


class ZLLExtendedColorLight(CustomDevice):
    """Philips ZigBee LightLink extended color bulb device."""

    signature = {
        MODELS_INFO: [
            (PHILIPS, "LCT001"),
            (PHILIPS, "LCT002"),
            (PHILIPS, "LCT003"),
            (PHILIPS, "LCT007"),
            (PHILIPS, "LCT010"),
            (PHILIPS, "LCT011"),
            (PHILIPS, "LCT012"),
            (PHILIPS, "LCT014"),
            (PHILIPS, "LCT015"),
            (PHILIPS, "LCT016"),
            (PHILIPS, "LCT021"),
            (PHILIPS, "LCT024"),
            (PHILIPS, "LLC020"),
            (PHILIPS, "LCF002"),
            (PHILIPS, "LCS001"),
        ],
        ENDPOINTS: {
            11: {
                # <SimpleDescriptor endpoint=11 profile=49246 device_type=528
                # device_version=2
                # input_clusters=[0, 3, 4, 5, 6, 8, 4096, 768, 64513]
                # output_clusters=[25]
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    Color.cluster_id,
                    64513,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
                # input_clusters=[33]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PhilipsOnOffCluster,
                    PhilipsLevelControlCluster,
                    LightLink.cluster_id,
                    PhilipsColorCluster,
                    64513,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class ZLLExtendedColorLight2(CustomDevice):
    """Philips ZigBee LightLink extended color bulb device without input cluster 64513."""

    signature = {
        MODELS_INFO: [(PHILIPS, "LCT012")],
        ENDPOINTS: {
            11: {
                # <SimpleDescriptor endpoint=11 profile=49246 device_type=528
                # device_version=2
                # input_clusters=[0, 3, 4, 5, 6, 8, 4096, 768, 64513]
                # output_clusters=[25]
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
                # input_clusters=[33]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PhilipsOnOffCluster,
                    PhilipsLevelControlCluster,
                    LightLink.cluster_id,
                    PhilipsColorCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
