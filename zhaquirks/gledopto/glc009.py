"""GLEDOPTO GL-C-009 device."""

from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
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
from zhaquirks.gledopto import GLEDOPTO


class GLC009(CustomDevice):
    """GLEDOPTO GL-C-009 device."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=11, profile=49246,
        # device_type=256, device_version=2,
        # input_clusters=[0, 3, 4, 5, 6, 8, 768], output_clusters=[])
        MODELS_INFO: [(GLEDOPTO, "GL-C-009")],
        ENDPOINTS: {
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # SizePrefixedSimpleDescriptor(endpoint=13, profile=49246,
            # device_type=256, device_version=2, input_clusters=[4096],
            # output_clusters=[4096])
            13: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }
