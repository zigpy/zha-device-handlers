"""Aqara H1 double rocker switch quirks. Also see opple_switch.py for similar double rocker switches."""
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, DeviceTemperatureCluster, MeteringCluster
from zhaquirks.xiaomi.aqara.opple_switch import XiaomiOpple2ButtonSwitchBase


class XiaomiOpple2ButtonSwitchFace2(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Face 2."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n2aeu1")],
        ENDPOINTS: {
            #  input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    DeviceTemperatureCluster.cluster_id,  # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    Alarms.cluster_id,  # 9
                    MeteringCluster.cluster_id,  # 0x0702
                    0x0B04,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            #  input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
