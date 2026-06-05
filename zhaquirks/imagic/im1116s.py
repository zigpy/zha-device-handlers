"""Device handler for GreatStar iMagic 1116-S sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.imagic import IMAGIC

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513
MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC02  # decimal = 64514


class iMagic1116(CustomDevice):
    """Custom device representing iMagic 1116-S sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821, 64513, 64514]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [(IMAGIC, "1116-S")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Identify.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID_2,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Identify.cluster_id],
            },
        }
    }
