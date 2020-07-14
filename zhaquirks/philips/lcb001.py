"""Quirk for Phillips LCB001."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    OnOff,
    Basic,
    Identify,
    LevelControl,
    Scenes,
    Groups,
    Ota,
    GreenPowerProxy,
)

from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    ENDPOINTS,
    OUTPUT_CLUSTERS,
    INPUT_CLUSTERS,
    DEVICE_TYPE,
    PROFILE_ID,
    MODELS_INFO,
)
from zhaquirks.philips import PHILIPS, PhilipsOnOffCluster


class PhilipsLCB001(CustomDevice):
    """Philips LCB001 device."""

    signature = {
        MODELS_INFO: [(PHILIPS, "LCB001")],
        ENDPOINTS: {
            11: {
                # <SimpleDescriptor endpoint=11 profile=260 device_type=269
                # device_version=1
                # input_clusters=[0, 3, 4, 5, 6, 8, 4096, 64514, 768, 64513]
                # output_clusters=[25]>
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    64514,
                    Color.cluster_id,
                    64513,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
                # input_clusters=[]
                # output_clusters=[33]>
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
                DEVICE_TYPE: zha.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    PhilipsOnOffCluster,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    64514,
                    Color.cluster_id,
                    64513,
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
