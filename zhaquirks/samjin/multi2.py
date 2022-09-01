"""Samjin Multi 2019 Refresh Quirk."""
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.samjin import SAMJIN
from zhaquirks.smartthings import SmartThingsAccelCluster


class SmartthingsMultiPurposeSensor2019(CustomDevice):
    """Samjin multi device."""

    signature = {
        MODELS_INFO: [(SAMJIN, "multi")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
            # device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280,
            # 2821, 64514]
            # output_clusters=[3, 25]>
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                    SmartThingsAccelCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                    SmartThingsAccelCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
