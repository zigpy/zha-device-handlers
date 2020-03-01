"""Quirk for lumi.sen_ill.mgl01 illumination sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zdo.types import NodeDescriptor

from .. import LUMI, BasicCluster, XiaomiCustomDevice
from ... import PowerConfigurationCluster
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)


class Illumination(XiaomiCustomDevice):
    """Aqara LUMI lumi.sen_ill.mgl01."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=262
        # device_version=1
        # input_clusters=[0, 1024, 3, 1]
        # output_clusters=[3]>
        MODELS_INFO: [(LUMI, "lumi.sen_ill.mgl01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.LIGHT_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    PowerConfigurationCluster.cluster_id,
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
