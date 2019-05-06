"""Xiaomi aqara smart motion sensor device."""
import asyncio
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import (
    Basic, Groups, Identify, MultistateInput, Ota, Scenes)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.xiaomi import (
    BasicCluster, PowerConfigurationCluster, TemperatureMeasurementCluster,
    XiaomiCustomDevice)

VIBE_DEVICE_TYPE = 0x5F02  # decimal = 24322
RECENT_ACTIVITY_LEVEL_ATTR = 0x0505  # decimal = 1285
ACCELEROMETER_ATTR = 0x0508  # decimal = 1288
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
ROTATION_DEGREES_ATTR = 0x0503  # decimal = 1283
STATIONARY_VALUE = 0
VIBE_VALUE = 1
TILT_VALUE = 2
DROP_VALUE = 3
MEASUREMENT_TYPE = {
    STATIONARY_VALUE: "Stationary",
    VIBE_VALUE: "Vibration",
    TILT_VALUE: "Tilt",
    DROP_VALUE: "Drop"
}

_LOGGER = logging.getLogger(__name__)


class VibrationAQ1(XiaomiCustomDevice):
    """Xiaomi aqara smart motion sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    class VibrationBasicCluster(BasicCluster):
        """Vibration cluster."""

        cluster_id = BasicCluster.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            super().__init__(*args, **kwargs)
            self.attributes.update({
                0xFF0D: ('sensitivity', types.uint8_t),
            })

    class MultistateInputCluster(CustomCluster, MultistateInput):
        """Multistate input cluster."""

        cluster_id = DoorLock.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                self._current_state[STATUS_TYPE_ATTR] = MEASUREMENT_TYPE.get(
                    value
                )
                if value == VIBE_VALUE:
                    self.endpoint.device.motion_bus.listener_event(
                        'motion_event'
                    )
                elif value == DROP_VALUE:
                    self.listener_event(
                        'zha_send_event',
                        self,
                        self._current_state[STATUS_TYPE_ATTR],
                        {}
                    )
            elif attrid == ROTATION_DEGREES_ATTR:
                self.listener_event(
                    'zha_send_event',
                    self,
                    self._current_state[STATUS_TYPE_ATTR],
                    {
                        'degrees': value
                    }
                )
            elif attrid == RECENT_ACTIVITY_LEVEL_ATTR:
                # these seem to be sent every minute when vibration is active
                self.endpoint.device.motion_bus.listener_event(
                    'motion_event'
                )

            # show something in the sensor in HA
            super()._update_attribute(
                0,
                self._current_state[STATUS_TYPE_ATTR]
            )

    class MotionCluster(LocalDataCluster, IasZone):
        """Motion cluster."""

        cluster_id = IasZone.cluster_id
        ZONE_STATE = 0x0000
        ZONE_TYPE = 0x0001
        ZONE_STATUS = 0x0002
        VIBRATION_TYPE = 0x002d
        ON = 1
        OFF = 0

        def __init__(self, *args, **kwargs):
            """Init."""
            super().__init__(*args, **kwargs)
            self._timer_handle = None
            self.endpoint.device.motion_bus.add_listener(self)
            self._update_attribute(self.ZONE_STATE, self.OFF)
            self._update_attribute(self.ZONE_TYPE, self.VIBRATION_TYPE)
            self._update_attribute(self.ZONE_STATUS, self.OFF)

        def motion_event(self):
            """Motion event."""
            super().listener_event(
                'cluster_command',
                None,
                self.ZONE_STATE,
                [self.ON]
            )
            super().listener_event(
                'cluster_command',
                None,
                self.ZONE_STATUS,
                [self.ON]
            )

            if self._timer_handle:
                self._timer_handle.cancel()

            loop = asyncio.get_event_loop()
            self._timer_handle = loop.call_later(75, self._turn_off)

        def _turn_off(self):
            self._timer_handle = None
            super().listener_event(
                'cluster_command',
                None,
                self.ZONE_STATE,
                [self.OFF]
            )
            super().listener_event(
                'cluster_command',
                None,
                self.ZONE_STATUS,
                [self.OFF]
            )

    signature = {
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.vibration.aq1',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DOOR_LOCK,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                DoorLock.cluster_id
            ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                Ota.cluster_id,
                DoorLock.cluster_id
            ],
        },
        2: {
            'profile_id': zha.PROFILE_ID,
            'device_type': VIBE_DEVICE_TYPE,
            'input_clusters': [
                Identify.cluster_id,
                MultistateInput.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                MultistateInput.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.vibration.aq1',
                'device_type': zha.DeviceType.DOOR_LOCK,
                'input_clusters': [
                    VibrationBasicCluster,
                    PowerConfigurationCluster,
                    TemperatureMeasurementCluster,
                    Identify.cluster_id,
                    MotionCluster,
                    Ota.cluster_id,
                    MultistateInputCluster
                ],
                'output_clusters': [
                    VibrationBasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    DoorLock.cluster_id
                ],
            },
            2: {
                'manufacturer': 'LUMI',
                'model': 'lumi.vibration.aq1',
                'device_type': VIBE_DEVICE_TYPE,
                'input_clusters': [
                    Identify.cluster_id
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id
                ],
            }
        },
    }
