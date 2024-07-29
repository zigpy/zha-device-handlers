"""Innr SP 234 plug."""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
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
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
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
from zhaquirks.innr import INNR, ElectricalMeasurementClusterInnr, MeteringClusterInnr


class SP234(CustomDevice):
    """Innr SP 234 smart plug."""

    signature = {
        MODELS_INFO: [(INNR, "SP 234")],
        ENDPOINTS: {
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
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                    0xFC57,
                    0xFC82,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
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
                    OnOff.cluster_id,
                    MeteringClusterInnr,
                    ElectricalMeasurementClusterInnr,
                    Diagnostic.cluster_id,
                    LightLink.cluster_id,
                    0xFC57,
                    0xFC82,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
