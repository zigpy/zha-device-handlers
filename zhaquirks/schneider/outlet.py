"""Schneider Electric (Wiser) Outlet Quirks."""
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


class MeteringCluster(CustomCluster, Metering):
    """Fix the Instantaneous Demand value x1000"""

    INSTANTANEOUS_DEMAND = 0x0400

    def _update_attribute(self, attrid, value):
        if attrid == self.INSTANTANEOUS_DEMAND:
            value = value / 1000.0
        super()._update_attribute(attrid, value)


class SocketOutlet(CustomDevice):
    """Schneider Electric Socket outlet WDE002182,WDE002172."""

    signature = {
        MODELS_INFO: [
            ("Schneider Electric", "SOCKET/OUTLET/1"),
            ("Schneider Electric", "SOCKET/OUTLET/2"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=9
            # device_version=0
            # input_clusters=[0, 3, 4, 5, 6, 1794, 1800, 2820, 2821, 64516] output_clusters=[25]>
            6: {
                PROFILE_ID: 0x0104,
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
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
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
            6: {
                PROFILE_ID: 0x0104,
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
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
