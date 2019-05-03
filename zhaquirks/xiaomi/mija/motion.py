"""Xiaomi mija body sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, LevelControl, OnOff, Ota, Scenes)

from zhaquirks import Bus
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice)

from .. import MotionCluster, OccupancyCluster

XIAOMI_CLUSTER_ID = 0xFFFF
_LOGGER = logging.getLogger(__name__)


class Motion(XiaomiCustomDevice):
    """Custom device representing mija body sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=263
        #  device_version=1
        #  input_clusters=[0, 65535, 3, 25]
        #  output_clusters=[0, 3, 4, 5, 6, 8, 25]>
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_motion',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DIMMER_SWITCH,
            'input_clusters': [
                Basic.cluster_id,
                XIAOMI_CLUSTER_ID,
                Ota.cluster_id,
                Identify.cluster_id
            ],
            'output_clusters': [
                Basic.cluster_id,
                Ota.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_motion',
                'device_type': zha.DeviceType.OCCUPANCY_SENSOR,
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    OccupancyCluster,
                    MotionCluster,
                    XIAOMI_CLUSTER_ID
                ],
                'output_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id
                ],
            }
        },
    }
