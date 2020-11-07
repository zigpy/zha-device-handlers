"""SmartThings SmartSense Multi Sensor quirk."""
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

SMARTSENSE_MULTI_DEVICE_TYPE = 0x0139  # decimal = 313


class IasZoneContactSwitchCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    ZONE_TYPE = 0x0001
    CONTACT_SWITCH_TYPE = 0x0015
    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: CONTACT_SWITCH_TYPE}


class SmartthingsSmartSenseMultiSensor(CustomDevice):
    """Multipurpose sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=313
        #  device_version=0 input_clusters=[0] output_clusters=[25]>
        MODELS_INFO: [(SMART_THINGS, "PGC313")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: SMARTSENSE_MULTI_DEVICE_TYPE,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            #  <SimpleDescriptor endpoint=2 profile=64513 device_type=313
            #  device_version=0 input_clusters=[] output_clusters=[]>
            2: {
                PROFILE_ID: 0xFC01,  # decimal = 64513
                DEVICE_TYPE: SMARTSENSE_MULTI_DEVICE_TYPE,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id, IasZoneContactSwitchCluster],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
