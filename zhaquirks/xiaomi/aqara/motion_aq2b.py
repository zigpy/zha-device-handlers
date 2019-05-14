"""Xiaomi aqara body sensor."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks import Bus
from zhaquirks.xiaomi import BasicCluster, XiaomiCustomDevice

from .. import MotionCluster, OccupancyCluster
from . import IlluminanceMeasurementCluster

XIAOMI_CLUSTER_ID = 0xFFFF


class MotionAQ2(XiaomiCustomDevice):
    """Custom device representing aqara body sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=260
        #  device_version=1
        #  input_clusters=[0, 65535, 1030, 1024]
        #  output_clusters=[0, 25]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_motion.aq2',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DIMMER_SWITCH,
            'input_clusters': [
                Basic.cluster_id,
                XIAOMI_CLUSTER_ID,
                OccupancySensing.cluster_id,
                IlluminanceMeasurementCluster.cluster_id,
            ],
            'output_clusters': [
                Basic.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_motion.aq2',
                'input_clusters': [
                    BasicCluster,
                    IlluminanceMeasurementCluster,
                    OccupancyCluster,
                    MotionCluster,
                    XIAOMI_CLUSTER_ID
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Ota.cluster_id
                ],
            }
        },
    }
