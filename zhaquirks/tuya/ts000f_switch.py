"""tuya TS000F xkap8wtb On/Off In-line Switches with metering support."""

from zigpy.profiles import zgp, zha
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
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaZB1888Cluster,
    TuyaZBE000Cluster,
    TuyaZBElectricalMeasurement,
    TuyaZBMeteringCluster,
    TuyaZBOnOffAttributeCluster,
)
from zhaquirks.tuya.mcu import EnchantedDevice


class Tuya_1G_Wall_Switch_Metering(EnchantedDevice):
    """Tuya 1 gang wall switch with metering and restore power state support."""

    signature = {
        MODEL: "TS000F",
        ENDPOINTS: {
            # SizePrefixedSimpleDescriptor(endpoint=242, profile=41440, device_type=97, device_version=0, input_clusters=[], output_clusters=[33])
            # input_clusters=["0x0000","0x0003","0x0004","0x0005","0x0006", "0x000a", "0x0702","0x0b04","0x1000","0x1888","0xe000"]
            # output_clusters=["0x0019"]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    TuyaZBMeteringCluster.cluster_id,
                    TuyaZBElectricalMeasurement.cluster_id,
                    LightLink.cluster_id,
                    TuyaZB1888Cluster.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=["0x0021"]>
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
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    Time.cluster_id,
                    TuyaZBMeteringCluster,
                    TuyaZBElectricalMeasurement,
                    LightLink.cluster_id,
                    TuyaZB1888Cluster,
                    TuyaZBE000Cluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
