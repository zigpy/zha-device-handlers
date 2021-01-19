"""Smart Things multi purpose sensor quirk."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from . import SmartThingsAccelCluster


class SmartthingsMultiPurposeSensor(CustomDevice):
    """Custom device representing a Smartthings Multi Purpose Sensor."""

    signature = {
        "endpoints": {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
            # device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280, 64514]
            # output_clusters=[3, 25]>
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.IAS_ZONE,
                "input_clusters": [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    SmartThingsAccelCluster.cluster_id,
                ],
                "output_clusters": [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }

    replacement = {
        "endpoints": {
            1: {
                "input_clusters": [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    SmartThingsAccelCluster.cluster_id,
                    SmartThingsAccelCluster,
                ],
                "output_clusters": [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
