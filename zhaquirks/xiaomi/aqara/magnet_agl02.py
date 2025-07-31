"""Quirk for Aqara T1 door sensor lumi.magnet.agl02."""

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import Cluster, foundation
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    BatterySize,
)
from zhaquirks.xiaomi import (
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)


class MagnetT1(XiaomiCustomDevice):
    """Aqara T1 door sensor quirk."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = BatterySize.CR1632
        super().__init__(*args, **kwargs)

    def _find_zcl_cluster(
        self, hdr: foundation.ZCLHeader, packet: t.ZigbeePacket
    ) -> Cluster:
        """Find a cluster for the packet."""
        assert packet.src_ep is not None
        endpoint = self.endpoints[packet.src_ep]

        # The `direction` field is incorrectly set, we should always route the packet
        # to client `OnOff` cluster
        if packet.cluster_id == OnOff.cluster_id:
            return endpoint.out_clusters[packet.cluster_id]

        return super()._find_zcl_cluster(hdr, packet)

    signature = {
        MODELS_INFO: [("LUMI", "lumi.magnet.agl02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
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
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    XiaomiAqaraE1Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
