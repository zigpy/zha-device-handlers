"""Tuya TS0121 plug."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaZBOnOffRestorePowerCluster


class TuyaMeteringCluster(CustomCluster, Metering):
    """TuyaMeteringCluster divides the kWh for tuya."""
    
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 0.01, DIVISOR: 100}


class Plug(CustomDevice):
    """Tuya TS0121 plug with restore tuya power state support."""

    signature = {
        MODEL: "TS0121",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 4, 5, 6, 9, 1794, 2820]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffRestorePowerCluster,
                    TuyaMeteringCluster,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
