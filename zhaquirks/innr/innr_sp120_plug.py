"""Innr SP 120 plug."""
from zigpy.profiles import zll
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

MANUFACTURER = "innr"
MODEL = "SP 120"


class MeteringCluster(CustomCluster, Metering):
    """Fix multiplier and divisor."""

    cluster_id = Metering.cluster_id
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 100}


class ElectricalMeasurementCluster(CustomCluster, ElectricalMeasurement):
    """Fix multiplier and divisor."""

    cluster_id = ElectricalMeasurement.cluster_id
    MULTIPLIER = 0x0602
    DIVISOR = 0x0603
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}


class SP120(CustomDevice):
    """Innr SP 120 smart plug."""

    signature = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 0x1000,
                INPUT_CLUSTERS: [
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
        MODELS_INFO: [(MANUFACTURER, MODEL)],
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_PLUGIN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ElectricalMeasurementCluster,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    MeteringCluster,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 0x1000,
                INPUT_CLUSTERS: [
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
