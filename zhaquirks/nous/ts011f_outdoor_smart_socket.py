"""Nous A4Z Outdoor 2 plug with metering."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
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


class MeteringCluster(CustomCluster, Metering):
    """Correct wrong metering with Nous A4Z."""

    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 100}


class TuyaZBElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Divides the Current for tuya."""

    AC_CURRENT_MULTIPLIER = 0x0602
    AC_CURRENT_DIVISOR = 0x0603
    _CONSTANT_ATTRIBUTES = {AC_CURRENT_MULTIPLIER: 1, AC_CURRENT_DIVISOR: 1000}


class NousOutdoor2Plug(CustomDevice):
    """Nous A4Z Outdoor 2 plug with metering."""

    signature = {
        MODELS_INFO: [("_TZ3000_uwkja6z1", "TS011F")],
        ENDPOINTS: {
            1: {
                "profile_id": 0x0104,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    0x0B04,
                    0xE000,
                    0xE001,
                ],
                "output_clusters": [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                "profile_id": 0x0104,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    0x0B04,
                    0xE000,
                    0xE001,
                ],
                "output_clusters": [],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": 0x0104,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MeteringCluster,
                    TuyaZBElectricalMeasurement,
                    0xE000,
                    0xE001,
                ],
                "output_clusters": [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                "profile_id": 0x0104,
                "device_type": zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                "input_clusters": [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    0xE000,
                    0xE001,
                ],
                "output_clusters": [],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
