from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import BasicCluster, XiaomiAqaraE1Cluster, XiaomiCustomDevice


class OppleClusterLight(XiaomiAqaraE1Cluster):
    """Add Opple cluster for power outage memory attribute."""

    attributes = {
        0x0201: ("power_outage_memory", t.Bool, True),
    }


class LumiLightAcn003(XiaomiCustomDevice):
    """Aqara ceiling light L1-350 also known as Xiaomi ZNXDD01LM.

    Provides dimmable light control with color temperature setting.
    This quirk adds support for power on behavior by adding OppleCluster.power_outage_memory attribute.
    """

    signature = {
        MODELS_INFO: [
            ("Aqara", "lumi.light.acn003"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    OppleClusterLight.cluster_id,  # 0xFCC0 - Manufacture Specific
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    OppleClusterLight,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            }
        }
    }
