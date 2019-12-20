"""Smart Things multi purpose sensor quirk."""

import zigpy.types as t
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Identify,
    PollControl,
    Ota,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC02  # decimal = 64514


class SmartThingsAccelCluster(CustomCluster):
    """SmartThings Acceleration Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Smartthings Accelerometer"
    ep_attribute = "accelerometer"
    attributes = {
        0x0000: ("motion_threshold_multiplier", t.uint8_t),
        0x0002: ("motion_threshold", t.uint16_t),
        0x0010: ("acceleration", t.bitmap8),  # acceleration detected
        0x0012: ("x_axis", t.int16s),
        0x0013: ("y_axis", t.int16s),
        0x0014: ("z_axis", t.int16s),
    }

    client_commands = {}
    server_commands = {}


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
