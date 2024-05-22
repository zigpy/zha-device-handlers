"""Xiaomi Aqara T1 motion sensor device lumi.motion.acn001."""
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

XIAOMI_CLUSTER_ID = 0xFCC0


class XiaomiManufacturerCluster(XiaomiAqaraE1Cluster):
    """Xiaomi manufacturer cluster."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 274:
            value = value - 65536
            self.endpoint.illuminance.update_attribute(
                IlluminanceMeasurement.AttributeDefs.measured_value.id, value
            )
            self.endpoint.occupancy.update_attribute(
                OccupancySensing.AttributeDefs.occupancy.id,
                OccupancySensing.Occupancy.Occupied,
            )


class MotionACN001(XiaomiCustomDevice):
    """Xiaomi motion sensor device lumi.motion.acn001."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        self.motion_bus = Bus()
        self.illuminance_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.motion.acn001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    0x0000,
                    0x0001,
                    0x0003,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0019,
                ],
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
