"""Xiaomi aqara E1 contact sensor device."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

XIAOMI_CLUSTER_ID = 0xFCC0


class MagnetE1(XiaomiCustomDevice):
    """Xiaomi contact sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=1
        #  input_clusters=[0, 1, 3, 1280, 64704]
        #  output_clusters=[3, 19]>
        MODELS_INFO: [(LUMI, "lumi.magnet.acn001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    XiaomiAqaraE1Cluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
