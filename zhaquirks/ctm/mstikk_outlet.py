"""CTM Lyng mStikk Outlet"""
from zigpy import types as t
import zigpy.profiles.zha as zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    DeviceTemperature,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
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
from zhaquirks.ctm import CTM, CtmDiagnosticsCluster, CtmStoveGuardCluster


class CtmOnOffCluster(CustomCluster, OnOff):
    """CTM Lyng custom on/off cluster."""

    attributes = OnOff.attributes.copy()
    attributes.update(
        {
            0x5000: ("current_flag", t.uint8_t, True),
        }
    )


class CtmLyngMStikkOutlet(CustomDevice):
    """CTM Lyng custom device mStikk outlet."""

    signature = {
        MODELS_INFO: [
            (CTM, "mStikk Outlet"),
            (CTM, "mStikk 16A"),
            (CTM, "mStikk 25A"),
            (CTM, "Tavlerele 25A"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=9
            # device_version=1
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 1794, 2820, 4096, 65261]
            # output_clusters=[3, 25, 65481]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    CtmStoveGuardCluster.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CtmOnOffCluster,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    CtmDiagnosticsCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    CtmStoveGuardCluster,
                ],
            },
        },
    }
