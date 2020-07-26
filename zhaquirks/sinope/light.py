"""
This module handles quirks of the  Sinopé Technologies light SW2500ZB and dimmer DM2500ZB.
manufacturer specific cluster implements attributes to control displaying 
setting occupancy on/off.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    DeviceTemperature,
    Groups,
    Identify,
    OnOff,
    LevelControl,
    Ota,
    Scenes,
)

from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.foundation import Status
from zigpy.zcl.clusters.smartenergy import Metering

from . import SINOPE
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    cluster_id = SINOPE_MANUFACTURER_CLUSTER_ID
    name = "Sinopé Technologies Manufacturer specific"
    ep_attribute = "sinope_manufacturer_specific"
    manufacturer_attributes = {
        0x0020: ("secs_since_2k", t.uint32_t),
    }


class SinopeTechnologiesLightingCluster(CustomCluster, lighting):
    """SinopeTechnologiesLightingCluster custom cluster."""

    manufacturer_attributes = {0x0400: ("set_occupancy", t.enum8)}


class SinopeTechnologieslight(CustomDevice):
    """SinopeTechnologiesLight custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=259
        # device_version=0 input_clusters=[0, 2, 3, 4, 5, 6, 1794, 2821,
        # 65281] output_clusters=[65281, 3, 4, 25]>
        MODELS_INFO: [(SINOPE, "SW2500ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    DeviceTemperature,
                    Identify,
                    Groups,
                    Scenes,
                    OnOff,
                    Metering,
                    Diagnostic,
                    SinopeTechnologiesLightingCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify,
                    Groups,
                    Ota,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        }
    }


class SinopeDM2500ZB(SinopeTechnologieslight):
    """DM2500ZB Dimmer."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
        # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2821, 65281]
        # output_clusters=[3, 4, 25, 65281]>
        MODELS_INFO: [(SINOPE, "DM2500ZB")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic,
                    DeviceTemperature,
                    Identify,
                    Groups,
                    Scenes,
                    OnOff,
                    LevelControl,
                    Metering,
                    Diagnostic,
                    SinopeTechnologiesLightingCluster,
                    SinopeTechnologiesManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify,
                    Groups,
                    Ota,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
            }
        }
    }
