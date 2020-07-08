"""Quirk for Philips SML002."""
from zigpy.profiles import zha, zll
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)

from . import PHILIPS
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class OccupancyCluster(CustomCluster, OccupancySensing):
    """philips occupancy cluster."""

    manufacturer_attributes = {
        0x0030: ("sensitivity", t.uint8_t),
        0x0031: ("sensitivity_max", t.uint8_t),
    }


class PhilipsSML002(CustomDevice):
    """philips SML002 device."""

    signature = {
        MODELS_INFO: [(PHILIPS, "SML002")],
        ENDPOINTS: {
            #  <SimpleDescriptor endpoint=1 profile=49246 device_type=0x0850
            #  device_version=?
            #  input_clusters=[0]
            #  output_clusters=[0, 3, 4, 5, 6, 8, 768]>
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=0x0107
            #  device_version=?
            #  input_clusters=[0, 1, 3, 1024, 1026, 1030]
            #  output_clusters=[25]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    OccupancyCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        }
    }
