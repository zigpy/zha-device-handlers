"""SmartThings SmartSense Motion quirk."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota

from . import SMART_THINGS, SmartThingsIasZone
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SMARTSENSE_MOTION_DEVICE_TYPE = 0x013A  # decimal = 314


class IasZoneMotionCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    ZONE_TYPE = 0x0001
    MOTION_TYPE = 0x000D
    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: MOTION_TYPE}


class SmartthingsSmartSenseMotionSensor(CustomDevice):
    """SmartSense Motion Sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=314
        #  device_version=0 input_clusters=[0] output_clusters=[25]>
        MODELS_INFO: [(SMART_THINGS, "PGC314")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: SMARTSENSE_MOTION_DEVICE_TYPE,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            #  <SimpleDescriptor endpoint=2 profile=64513 device_type=314
            #  device_version=0 input_clusters=[] output_clusters=[]>
            2: {
                PROFILE_ID: 0xFC01,  # decimal = 64513
                DEVICE_TYPE: SMARTSENSE_MOTION_DEVICE_TYPE,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id, IasZoneMotionCluster],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
