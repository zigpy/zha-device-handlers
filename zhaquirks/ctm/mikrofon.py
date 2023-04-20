"""CTM Lyng Mikrofon"""
import zigpy.profiles.zha as zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota, PowerConfiguration
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ctm import (
    CTM,
    CtmDiagnosticsCluster,
    CtmGroupConfigCluster,
    CtmPowerConfiguration,
    CtmTemperatureMeasurement,
)


class CtmLyngMikrofon(CustomDevice):
    """Custom device mikrofon."""

    signature = {
        MODELS_INFO: [(CTM, "Mikrofon")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
            # device_version=1
            # input_clusters=[0, 1, 3, 1026, 1280, 65191, 65261]
            # output_clusters=[3, 6, 25, 4096]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    CtmGroupConfigCluster.cluster_id,
                    CtmDiagnosticsCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CtmPowerConfiguration,
                    Identify.cluster_id,
                    CtmTemperatureMeasurement,
                    IasZone.cluster_id,
                    CtmGroupConfigCluster,
                    CtmDiagnosticsCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }
