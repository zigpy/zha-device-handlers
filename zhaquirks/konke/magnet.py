"""Konke magnet sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from . import KONKE
from .. import PowerConfigurationCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

KONKE_CLUSTER_ID = 0xFCC0


class KonkeMagnet(CustomDevice):
    """Custom device representing konke magnet sensors."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 1280, 64704]
        # output_clusters=[3, 64704]>
        MODELS_INFO: [(KONKE, "3AFE270104020015")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            }
        }
    }


class KonkeMagnet2(CustomDevice):
    """Custom device representing konke magnet sensors without custom konke cluster."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 1280]
        # output_clusters=[3]>
        MODELS_INFO: [(KONKE, "3AFE130104020015")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        }
    }
