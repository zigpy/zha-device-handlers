"""Osram Smart+ AC05347 GU10 White."""
from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from . import OSRAM, OsramLightCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class SmartplusAC05347(CustomDevice):
    """Osram Smart+ AC05347 GU10 White."""

    signature = {
        # <SimpleDescriptor endpoint=3 profile=49246 device_type=544
        # device_version=1 input_clusters=[0, 3, 4, 5, 6, 8, 300, 4096, 64527]
        # output_clusters=[25]>
        MODELS_INFO: [(OSRAM, "Smart+ AC05347")],
        ENDPOINTS: {
            3: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    OsramLightCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            3: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    OsramLightCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
