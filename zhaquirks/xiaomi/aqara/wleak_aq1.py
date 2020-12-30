"""Xiaomi aqara leak sensor device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.security import IasZone

from .. import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
    ZONE_TYPE,
)


class CustomIasZone(CustomCluster, IasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Water_Sensor}


class LeakAQ1(XiaomiQuickInitDevice):
    """Xiaomi aqara leak sensor device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=1
        #  input_clusters=[0, 3, 1]
        #  output_clusters=[25]>
        MODELS_INFO: [(LUMI, "lumi.sensor_wleak.aq1")],
        NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    XiaomiPowerConfiguration,
                    CustomIasZone,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
