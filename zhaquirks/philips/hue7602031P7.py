"""Philips Hue Go 7602031P7 device."""

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
from zhaquirks.philips import PHILIPS, PhilipsEffectCluster


class Philips7602031P7(CustomDevice):
    """Philips 7602031P7 device."""

    signature = {
        MODELS_INFO: [
            (PHILIPS, "7602031P7"),
        ],
        ENDPOINTS: {
            #  <SimpleDescriptor endpoint=11 profile=260 device_type=269
            #  device_version=1
            #  input_clusters=[0, 3, 4, 5, 6, 8, 768, 4096, 64513, 64515]
            #  output_clusters=[25]>
            11: {
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
                    64513,
                    64515,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            #  <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            #  device_version=0
            #  input_clusters=[]
            #  output_clusters=[33]>
            242: {
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
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    64513,
                    PhilipsEffectCluster,
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
