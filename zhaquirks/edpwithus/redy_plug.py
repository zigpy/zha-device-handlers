"""EDP WithUs SmartPlug Quirk."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.smartenergy import Metering

from . import MeteringCluster


class EdpWithUsSmartPlug(CustomDevice):
    """Tradfri Plug."""

    signature = {
        "endpoints": {
            # <SimpleDescriptor endpoint=85 profile=260 device_type=9
            # device_version=0
            # input_clusters=[0, 3, 4, 5, 6, 9, 10, 1794] output_clusters=[25]>
            85: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.MAIN_POWER_OUTLET,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Time.cluster_id,
                    Metering.cluster_id,
                ],
                "output_clusters": [Ota.cluster_id],
            }
        },
        "manufacturer": "EDP-WITHUS",
    }

    replacement = {
        "endpoints": {
            85: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Time.cluster_id,
                    MeteringCluster,
                ],
                "output_clusters": [Ota.cluster_id],
            }
        }
    }
