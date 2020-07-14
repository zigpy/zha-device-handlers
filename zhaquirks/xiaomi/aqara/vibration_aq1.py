"""Xiaomi aqara smart motion sensor device."""
import asyncio
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    MultistateInput,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.security import IasZone

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ... import Bus, LocalDataCluster
from ...const import (
    CLUSTER_COMMAND,
    CLUSTER_ID,
    COMMAND,
    COMMAND_TILT,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
    UNKNOWN,
    ZHA_SEND_EVENT,
)

ACCELEROMETER_ATTR = 0x0508  # decimal = 1288
DROP_VALUE = 3
RECENT_ACTIVITY_LEVEL_ATTR = 0x0505  # decimal = 1285
ROTATION_DEGREES_ATTR = 0x0503  # decimal = 1283
SEND_EVENT = "send_event"
STATIONARY_VALUE = 0
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
TILT_VALUE = 2
TILTED = "device_tilted"
VIBE_DEVICE_TYPE = 0x5F02  # decimal = 24322
VIBE_VALUE = 1

MEASUREMENT_TYPE = {
    STATIONARY_VALUE: "Stationary",
    VIBE_VALUE: "Vibration",
    TILT_VALUE: "Tilt",
    DROP_VALUE: "Drop",
}

_LOGGER = logging.getLogger(__name__)


class VibrationAQ1(XiaomiCustomDevice):
    """Xiaomi aqara smart motion sensor device."""

    manufacturer_id_override = 0x115F

    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    class VibrationBasicCluster(BasicCluster):
        """Vibration cluster."""

        cluster_id = BasicCluster.cluster_id
        manufacturer_attributes = {0xFF0D: ("sensitivity", types.uint8_t)}

    class MultistateInputCluster(CustomCluster, MultistateInput):
        """Multistate input cluster."""

        cluster_id = DoorLock.cluster_id
        manufacturer_attributes = {0x0000: ("lock_state", types.uint8_t)}

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                self._current_state[STATUS_TYPE_ATTR] = MEASUREMENT_TYPE.get(
                    value, UNKNOWN
                )
                if value == VIBE_VALUE:
                    self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
                elif value == DROP_VALUE:
                    self.endpoint.device.motion_bus.listener_event(
                        SEND_EVENT, self._current_state[STATUS_TYPE_ATTR]
                    )
            elif attrid == ROTATION_DEGREES_ATTR:
                self.endpoint.device.motion_bus.listener_event(
                    SEND_EVENT,
                    self._current_state[STATUS_TYPE_ATTR],
                    {"degrees": value},
                )
            elif attrid == RECENT_ACTIVITY_LEVEL_ATTR:
                # these seem to be sent every minute when vibration is active
                self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)

            # show something in the sensor in HA
            if STATUS_TYPE_ATTR in self._current_state:
                super()._update_attribute(0, self._current_state[STATUS_TYPE_ATTR])

    class MotionCluster(LocalDataCluster, IasZone):
        """Motion cluster."""

        cluster_id = IasZone.cluster_id
        OFF = 0
        ON = 1
        VIBRATION_TYPE = 0x002D
        ZONE_STATE = 0x0000
        ZONE_STATUS = 0x0002
        ZONE_TYPE = 0x0001

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
            super().listener_event(CLUSTER_COMMAND, None, self.ZONE_STATE, [self.ON])
            super().listener_event(CLUSTER_COMMAND, None, self.ZONE_STATUS, [self.ON])

            if self._timer_handle:
                self._timer_handle.cancel()

            loop = asyncio.get_event_loop()
            self._timer_handle = loop.call_later(75, self._turn_off)

        def send_event(self, event, *args):
            """Send event."""
            self.listener_event(ZHA_SEND_EVENT, event, args)

        def _turn_off(self):
            self._timer_handle = None
            super().listener_event(CLUSTER_COMMAND, None, self.ZONE_STATE, [self.OFF])
            super().listener_event(CLUSTER_COMMAND, None, self.ZONE_STATUS, [self.OFF])

    signature = {
        MODELS_INFO: [(LUMI, "lumi.vibration.aq1")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    DoorLock.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    DoorLock.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: VIBE_DEVICE_TYPE,
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    VibrationBasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    MotionCluster,
                    Ota.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    VibrationBasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: VIBE_DEVICE_TYPE,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (TILTED, TILTED): {COMMAND: COMMAND_TILT, CLUSTER_ID: 1280, ENDPOINT_ID: 1}
    }
