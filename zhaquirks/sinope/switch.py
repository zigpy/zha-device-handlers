"""Module to handle quirks of the Sinopé Technologies switches SP2600ZB and SP2610ZB."""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sinope import SINOPE

SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01


class CustomMeteringCluster(CustomCluster, Metering):
    """Custom Metering Cluster."""

    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {DIVISOR: 1000}


class SinopeTechnologiesSwitch(CustomDevice):
    """SinopeTechnologiesSwitch custom device."""

    signature = {
        # <SimpleDescriptor(endpoint=1, profile=260,
        # device_type=81, device_version=0,
        # input_clusters=[0, 3, 6, 1794, 2820, 65281]
        # output_clusters=[25]>
        MODELS_INFO: [(SINOPE, "SP2600ZB"), (SINOPE, "SP2610ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
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
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    CustomMeteringCluster,
                    ElectricalMeasurement.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
