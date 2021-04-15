"""SmartThings SmartSense Multi Sensor quirk."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_TYPE,
)
from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone

SMARTSENSE_MULTI_DEVICE_TYPE = 0x0139  # decimal = 313


class IasZoneContactSwitchCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Contact_Switch}


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
