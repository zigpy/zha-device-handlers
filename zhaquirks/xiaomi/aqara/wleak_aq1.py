"""Xiaomi aqara leak sensor device."""
from zigpy import quirks
from zigpy.profiles import zha
from zigpy.quirks.xiaomi import AqaraWaterSensor
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.security import IasZone

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

#  remove the zigpy version of this device handler
if AqaraWaterSensor in quirks._DEVICE_REGISTRY:
    quirks._DEVICE_REGISTRY.remove(AqaraWaterSensor)


class LeakAQ1(XiaomiCustomDevice):
    """Xiaomi aqara leak sensor device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=1
        #  input_clusters=[0, 3, 1]
        #  output_clusters=[25]>
        MODELS_INFO: [(LUMI, "lumi.sensor_wleak.aq1")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
