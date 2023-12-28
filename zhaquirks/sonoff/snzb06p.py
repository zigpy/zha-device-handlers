"""Sonoff Smart Button SNZB-06P"""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SONOFF_CLUSTER_ID = 0xFC57
SONOFF_MANUFACTURER_ID = 0x1286


class IlluminationStatus(t.uint8_t):
    """Last captured state of illumination."""

    Dark = 0x00
    Light = 0x01


class SonoffCluster(CustomCluster):
    """Sonoff manufacture specific cluster that provides illuminance"""

    cluster_id = 0xFC11
    manufacturer_id_override = SONOFF_MANUFACTURER_ID

    attributes = {
        0x2001: ZCLAttributeDef(
            type=IlluminationStatus,
            access="r",
            is_manufacturer_specific=True,
            name="illuminantion",
        ),
    }


class SonoffPresenceSensorSNZB06P(CustomDevice):
    """Sonoff presence sensor - model SNZB-06P"""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=0
        #  device_version=1
        #  input_clusters=[0, 3, 32, 64599]
        #  output_clusters=[3, 25]>
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
                    SonoffCluster.cluster_id,
                    SONOFF_CLUSTER_ID,
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
                    SonoffCluster,
                    SONOFF_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
