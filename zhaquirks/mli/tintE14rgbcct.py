"""Tint E14 RGB CCT."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
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


class TintRGBCCTColorCluster(CustomCluster, Color):
    """Tint RGB+CCT Lighting custom cluster."""

    # Set correct capabilities to ct, xy, hs
    # Tint bulbs do not correctly report this attribute
    _CONSTANT_ATTRIBUTES = {0x400A: 0b11111}


class TintRGBCCTLight(CustomDevice):
    """Tint E14 RGB+CCT Lighting device."""

    signature = {
        MODELS_INFO: [("MLI", "tint-ExtendedColor")],
        ENDPOINTS: {
            1: {
                #   "profile_id": 260,
                #   "device_type": "0x010d",
                #   "in_clusters": [
                #     "0x0000",
                #     "0x0003",
                #     "0x0004",
                #     "0x0005",
                #     "0x0006",
                #     "0x0008",
                #     "0x0300",
                #     "0x1000",
                #     "0x100f"
                #   ],
                #   "out_clusters": [
                #     "0x0019"
                #   ]
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    4111,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                #   "profile_id": 41440,
                #   "device_type": "0x0061",
                #   "in_clusters": [],
                #   "out_clusters": [
                #     "0x0021"
                #   ]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    TintRGBCCTColorCluster,
                    LightLink.cluster_id,
                    4111,
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
