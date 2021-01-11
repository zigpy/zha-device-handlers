"""Tradfri Plug Quirk."""
from zigpy.profiles import zha, zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from . import IKEA

IKEA_CLUSTER_ID = 0xFC7C  # decimal = 64636


class TradfriPlug(CustomDevice):
    """Tradfri Plug."""

    signature = {
        "endpoints": {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=266
            # device_version=0
            # input_clusters=[0, 3, 4, 5, 6, 8, 64636] output_clusters=[5, 25, 32]>
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                "output_clusters": [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=49246 device_type=16
            # device_version=0
            # input_clusters=[4096] output_clusters=[4096]>
            2: {
                "profile_id": 0xC05E,
                "device_type": zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                "input_clusters": [LightLink.cluster_id],
                "output_clusters": [LightLink.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[33] output_clusters=[33]>
            242: {
                "profile_id": 0xA1E0,
                "device_type": 0x0061,
                "input_clusters": [33],
                "output_clusters": [33],
            },
        },
        "manufacturer": IKEA,
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                "output_clusters": [
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    PollControl.cluster_id,
                ],
            }
        }
    }
