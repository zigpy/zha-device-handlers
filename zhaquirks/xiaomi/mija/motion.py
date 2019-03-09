"""Xiaomi mija body sensor."""
import asyncio
import logging

from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.general import (
    Basic, Identify, Ota, Groups, Scenes, LevelControl, OnOff
)
from zigpy.quirks import CustomCluster
from zigpy.profiles import zha
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
)
from zhaquirks import Bus, LocalDataCluster


XIAOMI_CLUSTER_ID = 0xFFFF
_LOGGER = logging.getLogger(__name__)
OCCUPANCY_STATE = 0
ZONE_STATE = 0
ON = 1
OFF = 0


class Motion(XiaomiCustomDevice):
    """Custom device representing mija body sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        self.motionBus = Bus()
        super().__init__(*args, **kwargs)

    class OccupancyCluster(CustomCluster, OccupancySensing):
        """Occupancy cluster."""

        cluster_id = OccupancySensing.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            super().__init__(*args, **kwargs)
            self._timer_handle = None

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)

            if attrid == OCCUPANCY_STATE and value == ON:
                if self._timer_handle:
                    self._timer_handle.cancel()
                self.endpoint.device.motionBus.listener_event('motion_event')
                loop = asyncio.get_event_loop()
                self._timer_handle = loop.call_later(600, self._turn_off)

        def _turn_off(self):
            self._timer_handle = None
            self._update_attribute(OCCUPANCY_STATE, OFF)

    class MotionCluster(LocalDataCluster, IasZone):
        """Motion cluster."""

        cluster_id = IasZone.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            super().__init__(*args, **kwargs)
            self._timer_handle = None
            self.endpoint.device.motionBus.add_listener(self)

        def motion_event(self):
            """Motion event."""
            super().listener_event(
                'cluster_command',
                None,
                ZONE_STATE,
                [ON]
            )

            _LOGGER.debug(
                "%s - Received motion event message",
                self.endpoint.device._ieee
            )

            if self._timer_handle:
                self._timer_handle.cancel()

            loop = asyncio.get_event_loop()
            self._timer_handle = loop.call_later(120, self._turn_off)

        def _turn_off(self):
            _LOGGER.debug(
                "%s - Resetting motion sensor",
                self.endpoint.device._ieee
            )
            self._timer_handle = None
            super().listener_event(
                'cluster_command',
                None,
                ZONE_STATE,
                [OFF]
            )

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
