"""Sonoff SNZB-06 - Zigbee presence sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SONOFF_CLUSTER_FC11_ID = 0xFC11
SONOFF_CLUSTER_FC57_ID = 0xFC57
ATTR_SONOFF_ILLUMINATION_STATUS = 0x2001


class IlluminationStatus(t.enum8):
    """Last measureed state of illumination enum."""

    Dark = 0x00
    Light = 0x01


class SonoffFC11Cluster(CustomCluster):
    """Sonoff manufacture specific cluster that provides illuminance."""

    cluster_id = SONOFF_CLUSTER_FC11_ID
    ep_attribute = "sonoff_manufacturer"
    attributes = {
        ATTR_SONOFF_ILLUMINATION_STATUS: ("last_illumination_state", IlluminationStatus)
    }


class SonoffPresenceSenorSNZB06P(CustomDevice):
    """Sonoff human presence senor - model SNZB-06P."""

    signature = {
        # <SimpleDescriptor endpoint=1, profile=260, device_type=263
        # device_version=1
        # input_clusters=[0, 3, 1030, 1280, 64599, 64529]
        # output_clusters=[3, 25]>
        MODELS_INFO: [
            ("SONOFF", "SNZB-06P"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                    IasZone.cluster_id,
                    SONOFF_CLUSTER_FC11_ID,
                    SONOFF_CLUSTER_FC57_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                    SonoffFC11Cluster,
                    SONOFF_CLUSTER_FC57_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
