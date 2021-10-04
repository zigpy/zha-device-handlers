"""TS011F plug."""
import zigpy.types as t
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
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


class TuyaZBMetering(CustomCluster, Metering):
    """TuyaZBMetering cluster implementation. This implementation divides the KwH for tuya devices"""

    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 100}


class TuyaZBElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """TuyaZBElectricalMeasurement cluster implementation. This implementation divides the Current for tuya devices"""

    AC_VOLTAGE_MULTIPLIER = 0x0600
    AC_VOLTAGE_DIVISOR = 0x0601
    _CONSTANT_ATTRIBUTES = {AC_VOLTAGE_MULTIPLIER: 1, AC_VOLTAGE_DIVISOR: 1000}


class PowerOnState(t.enum8):
    """Tuya power on state enum."""

    Off = 0x00
    On = 0x01
    LastState = 0x02


class OnOffRestorePowerCluster(CustomCluster, OnOff):
    """Tuya on off cluster with restore state."""

    attributes = OnOff.attributes.copy()
    attributes.update({0x8002: ("power_on_state", PowerOnState)})


class Plug(CustomDevice):
    """Tuya plug with restore power state support."""

    signature = {
        MODEL: "TS011F",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=266 device_type=81
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 9, 1794, 2820, 57344, 57345]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    0xE000,  # Unknown
                    0xE001,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=1
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffRestorePowerCluster,
                    TuyaZBMetering,
                    TuyaZBElectricalMeasurement,
                    0xE000,  # Unknown
                    0xE001,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
