"""Schneider Electric (Wiser) Outlet Quirks."""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import DeviceManagement, Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.schneiderelectric import SE_MANUF_NAME


class MeteringCluster(CustomCluster, Metering):
    """Custom Metering cluster to fix instantaneous demand value multiplied by 1000."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.instantaneous_demand.id:
            value = value / 1000
        super()._update_attribute(attrid, value)


class SocketOutlet(CustomDevice):
    """Schneider Electric Socket outlet WDE002182, WDE002172."""

    signature = {
        MODELS_INFO: [
            (SE_MANUF_NAME, "SOCKET/OUTLET/1"),
            (SE_MANUF_NAME, "SOCKET/OUTLET/2"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=9
            # device_version=0
            # input_clusters=[0, 3, 4, 5, 6, 1794, 1800, 2820, 2821, 64516] output_clusters=[25]>
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    DeviceManagement.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    0xFC04,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MeteringCluster,
                    DeviceManagement.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    0xFC04,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
