"""Xiaomi aqara T1 motion sensor device."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing

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
    OccupancyCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

XIAOMI_CLUSTER_ID = 0xFCC0


class XiaomiManufacturerCluster(XiaomiAqaraE1Cluster):
    """Xiaomi manufacturer cluster."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 274:
            value = value - 65536
            self.endpoint.illuminance.illuminance_reported(value)
            self.endpoint.occupancy.update_attribute(0, 1)


class MotionT1(XiaomiCustomDevice):
    """Xiaomi motion sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        self.motion_bus = Bus()
        self.illuminance_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=263
        #  device_version=1
        #  input_clusters=[0, 1, 3, 1030]
        #  output_clusters=[3, 19]>
        MODELS_INFO: [(LUMI, "lumi.motion.agl02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
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
                    OccupancyCluster,
                    MotionCluster,
                    IlluminanceMeasurementCluster,
                    XiaomiManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
