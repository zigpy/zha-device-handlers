"""Osram Smart+ Plug device."""
from zigpy.profiles import zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.osram import OSRAM, OsramLightCluster


class OsramPlug(CustomDevice):
    """Osram Smart+ Plug."""

    signature = {
        MODELS_INFO: [(OSRAM, "Plug 01")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=3 profile=49246 device_type=16
            # device_version=2
            # input_clusters=[4096, 0, 3, 4, 5, 6, 2820, 64527]
            # output_clusters=[25]>
            3: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    OsramLightCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            3: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                    OsramLightCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }
