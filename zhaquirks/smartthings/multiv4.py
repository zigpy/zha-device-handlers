"""Device handler for smartthings multiV4 sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, BinaryInput, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import SMART_THINGS
from ..centralite import CentraLiteAccelCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class SmartThingsMultiV4(CustomDevice):
    """SmartThingsMultiV4."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 15, 32, 1026, 1280, 64514]
        # output_clusters=[25]>
        MODELS_INFO: [(SMART_THINGS, "multiv4")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    CentraLiteAccelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    CentraLiteAccelCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
