"""Quirk for Aqara illumination sensor."""

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)


class Illumination(XiaomiCustomDevice):
    """Aqara LUMI lumi.sen_ill.mgl01 illumination sensor."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=262
        # device_version=1
        # input_clusters=[0, 1, 3, 1024]
        # output_clusters=[3]>
        MODELS_INFO: [(LUMI, "lumi.sen_ill.mgl01"), ("XIAOMI", "lumi.sen_ill.mgl01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    PowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        },
    }


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster with configurable detection interval."""

    attributes = {
        0x0000: ("detection_interval", types.uint16_t, True),
    }


class IlluminationT1(XiaomiCustomDevice):
    """Aqara LUMI T1 illumination sensor with configurable detection interval."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.sen_ill.agl01")],
        ENDPOINTS: Illumination.signature[ENDPOINTS],
    }

    replacement = {
        NODE_DESCRIPTOR: Illumination.replacement[NODE_DESCRIPTOR],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    PowerConfigurationCluster,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        },
    }
