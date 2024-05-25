"""Xiaomi Aqara E1 motion sensor device lumi.motion.acn001."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing, IlluminanceMeasurement

from zhaquirks import Bus
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
    IlluminanceMeasurementCluster,
    MotionCluster,
    LocalOccupancyCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)
from zhaquirks.xiaomi.aqara.motion_agl02 import XiaomiManufacturerCluster


class MotionACN001(XiaomiCustomDevice):
    """Xiaomi motion sensor device lumi.motion.acn001."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.motion.acn001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    XiaomiAqaraE1Cluster.cluster_id,
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
                    LocalOccupancyCluster,
                    MotionCluster,
                    IlluminanceMeasurementCluster,
                    XiaomiManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
