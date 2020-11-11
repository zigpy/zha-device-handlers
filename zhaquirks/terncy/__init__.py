"""Module for Terncy quirks."""
import math

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    TemperatureMeasurement,
)

from .. import OCCUPANCY_EVENT, LocalDataCluster, OccupancyOnEvent, _Motion
from ..const import (
    BUTTON,
    CLUSTER_COMMAND,
    COMMAND,
    DOUBLE_PRESS,
    LEFT,
    MOTION_EVENT,
    ON,
    PRESS_TYPE,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    RIGHT,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
    ZONE_STATE,
)

CLICK_TYPES = {1: "single", 2: "double", 3: "triple", 4: "quadruple", 5: "quintuple"}
ROTATED = "device_rotated"
ROTATE_LEFT = "rotate_left"
ROTATE_RIGHT = "rotate_right"
SIDE_LOOKUP = {5: RIGHT, 7: RIGHT, 40: LEFT, 56: LEFT}
STEPS = "steps"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFCCC  # decimal = 64716
MOTION_TYPE = 0x000D
BUTTON_TRIGGERS = {
    (SHORT_PRESS, BUTTON): {COMMAND: "button_single"},
    (DOUBLE_PRESS, BUTTON): {COMMAND: "button_double"},
    (TRIPLE_PRESS, BUTTON): {COMMAND: "button_triple"},
    (QUADRUPLE_PRESS, BUTTON): {COMMAND: "button_quadruple"},
    (QUINTUPLE_PRESS, BUTTON): {COMMAND: "button_quintuple"},
}
KNOB_TRIGGERS = {
    (ROTATED, RIGHT): {COMMAND: ROTATE_RIGHT},
    (ROTATED, LEFT): {COMMAND: ROTATE_LEFT},
}
ZONE_TYPE = 0x0001


class IlluminanceMeasurementCluster(CustomCluster, IlluminanceMeasurement):
    """Terncy Illuminance Measurement Cluster."""

    cluster_id = IlluminanceMeasurement.cluster_id
    ATTR_ID = 0

    def _update_attribute(self, attrid, value):
        if attrid == self.ATTR_ID and value > 0:
            value = 10000 * math.log10(value) + 1
        super()._update_attribute(attrid, value)


class TemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """Terncy Temperature Cluster."""

    cluster_id = TemperatureMeasurement.cluster_id
    ATTR_ID = 0

    def _update_attribute(self, attrid, value):
        if attrid == self.ATTR_ID:
            value = value * 10.0
        super()._update_attribute(attrid, value)


class OccupancyCluster(OccupancyOnEvent):
    """Occupancy cluster."""


class MotionCluster(LocalDataCluster, _Motion):
    """Motion cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: MOTION_TYPE}
    reset_s: int = 5
    send_occupancy_event: bool = True

    def motion_event(self):
        """Motion event."""
        super().listener_event(CLUSTER_COMMAND, 254, ZONE_STATE, [ON, 0, 0, 0])

        if self._timer_handle:
            self._timer_handle.cancel()

        self._timer_handle = self._loop.call_later(self.reset_s, self._turn_off)

        if self.send_occupancy_event:
            self.endpoint.device.occupancy_bus.listener_event(OCCUPANCY_EVENT)


class MotionClusterLeft(MotionCluster):
    """Motion cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.motion_left_bus.add_listener(self)


class MotionClusterRight(MotionCluster):
    """Motion cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.motion_right_bus.add_listener(self)


class TerncyRawCluster(CustomCluster):
    """Terncy Raw Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "Terncy Raw cluster"
    # ep_attribute = "accelerometer"

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle a cluster command received on this cluster."""
        args = list(args)
        if command_id == 0:  # click event
            count = args[0]
            state = args[1]
            if state > 5:
                state = 5
            event_args = {PRESS_TYPE: CLICK_TYPES[state], "count": count, VALUE: state}
            action = "button_{}".format(CLICK_TYPES[state])
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
        elif command_id == 4:  # motion event
            state = args[2]
            side = SIDE_LOOKUP[state]
            if side == LEFT:
                self.endpoint.device.motion_left_bus.listener_event(MOTION_EVENT)
            elif side == RIGHT:
                self.endpoint.device.motion_right_bus.listener_event(MOTION_EVENT)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 27:  # knob rotate event
            if value > 0:
                action = ROTATE_RIGHT
            else:
                action = ROTATE_LEFT
            steps = value / 12
            event_args = {STEPS: abs(steps)}
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
