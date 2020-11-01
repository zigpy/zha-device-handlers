"""Osram tunable white device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lighting import Color

from . import OSRAM, OsramLightCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class OsramColorCluster(CustomCluster, Color):
    """Osram A19 tunable white device."""

    _CONSTANT_ATTRIBUTES = {0x400A: 16, 0x400C: 370}


class OsramTunableWhite(CustomDevice):
    """Osram tunable white device."""

    signature = {
        # <SimpleDescriptor endpoint=3 profile=260 device_type=258
        # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 768, 64527]
        # output_clusters=[25]>
        MODELS_INFO: [
            (OSRAM, "LIGHTIFY A19 Tunable White"),
            (OSRAM, "LIGHTIFY RT Tunable White"),
        ],
        ENDPOINTS: {
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    OsramLightCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    OsramColorCluster,
                    ElectricalMeasurement.cluster_id,
                    OsramLightCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
