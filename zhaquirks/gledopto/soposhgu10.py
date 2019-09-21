"""GLEDOPTO Soposh Dual White and color 5W GU10 300lm device."""
from zigpy.profiles import zll
from zigpy.profiles.zll import DeviceType
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
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class SoposhGU10(CustomDevice):
    """GLEDOPTO Soposh Dual White and color 5W GU10 300lm."""

    signature = {
        ENDPOINTS: {
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: DeviceType.EXTENDED_COLOR_LIGHT,
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
            13: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        }
    }

    replacement = {
        ENDPOINTS: {
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: DeviceType.EXTENDED_COLOR_LIGHT,
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
            }
        }
    }
