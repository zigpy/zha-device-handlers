import asyncio
import logging

from zigpy.zcl.clusters.measurement import IlluminanceMeasurement,\
    OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.general import Basic, PowerConfiguration,\
    Identify, Ota
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.profiles import zha
from zigpy.util import ListenableMixin
from xiaomi_common import BasicCluster, PowerConfigurationCluster

import homeassistant.components.zha.const as zha_const


XIAOMI_CLUSTER_ID = 0xFFFF
_LOGGER = logging.getLogger(__name__)
OCCUPANCY_STATE = 0
ZONE_STATE = 0
ON = 1
OFF = 0

if zha.PROFILE_ID not in zha_const.DEVICE_CLASS:
        zha_const.DEVICE_CLASS[zha.PROFILE_ID] = {}
zha_const.DEVICE_CLASS[zha.PROFILE_ID].update({
    zha.DeviceType.OCCUPANCY_SENSOR: 'binary_sensor'
})


class AqaraBodySensor(CustomDevice, ListenableMixin):
    _listeners = {}

    class OccupancyCluster(CustomCluster, OccupancySensing):
        cluster_id = OccupancySensing.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._timer_handle = None

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)

            if attrid == OCCUPANCY_STATE and value == ON:
                if self._timer_handle:
                    self._timer_handle.cancel()
                self.endpoint.device.listener_event('motion_event')
                loop = asyncio.get_event_loop()
                self._timer_handle = loop.call_later(600, self._turn_off)

        def _turn_off(self):
            self._timer_handle = None
            self._update_attribute(OCCUPANCY_STATE, OFF)

    class MotionCluster(CustomCluster, IasZone):
        cluster_id = IasZone.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._timer_handle = None
            self.endpoint.device.add_listener(self)

        def battery_reported(self, voltage):
            pass

        def motion_event(self):
            super().listener_event(
                'cluster_command',
                None,
                ZONE_STATE,
                [ON])

            _LOGGER.debug("%s - Received motion event message",
                          self.endpoint.device._ieee
                          )

            if self._timer_handle:
                self._timer_handle.cancel()

            loop = asyncio.get_event_loop()
            self._timer_handle = loop.call_later(120, self._turn_off)

        def _turn_off(self):
            _LOGGER.debug("%s - Resetting motion sensor",
                          self.endpoint.device._ieee
                          )
            self._timer_handle = None
            super().listener_event(
                'cluster_command',
                None,
                ZONE_STATE,
                [OFF])

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=263 device_version=1 input_clusters=[0, 65535, 1030, 1024, 1280, 1, 3] output_clusters=[0, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.OCCUPANCY_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                XIAOMI_CLUSTER_ID,
                OccupancySensing.cluster_id,
                IlluminanceMeasurement.cluster_id,
                IasZone.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id
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
                'input_clusters': [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    OccupancyCluster,
                    MotionCluster
                    ],
            }
        },
    }
