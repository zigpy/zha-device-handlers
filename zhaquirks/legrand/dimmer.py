"""Device handler for Legrand Dimmer switch w/o neutral."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from . import LEGRAND
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513


class LegrandCluster(CustomCluster, ManufacturerSpecificCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"
    manufacturer_attributes = {
        0x0000: ("dimmer", t.data16),
        0x0001: ("led_dark", t.Bool),
        0x0002: ("led_on", t.Bool),
    }


class DimmerWithoutNeutral(CustomDevice):
    """Dimmer switch w/o neutral."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 64513, 25]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch w/o neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, LegrandCluster, Ota.cluster_id],
            }
        }
    }


class DimmerWithoutNeutral2(DimmerWithoutNeutral):
    """Dimmer switch w/o neutral 2."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 64513, 25]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch w/o neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }
