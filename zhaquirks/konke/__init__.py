"""Konke sensors."""

import asyncio
import logging

from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.measurement import (
    OccupancySensing,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from .. import Bus, LocalDataCluster
from ..const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    CLUSTER_COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_TRIPLE,
    OFF,
    ON,
    UNKNOWN,
    VALUE,
    ZHA_SEND_EVENT,
    ZONE_STATE,
)

KONKE = "Konke"
OCCUPANCY_STATE = 0
OCCUPANCY_EVENT = "occupancy_event"
MOTION_TYPE = 0x000D
ZONE_TYPE = 0x0001

MOTION_TIME = 60
OCCUPANCY_TIME = 600

class OccupancyCluster(LocalDataCluster, OccupancySensing):
    """Occupancy cluster."""

    cluster_id = OccupancySensing.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._timer_handle = None
        self.endpoint.device.occupancy_bus.add_listener(self)

    def occupancy_event(self):
        """Occupancy event."""
        self._update_attribute(OCCUPANCY_STATE, ON)

        if self._timer_handle:
            self._timer_handle.cancel()

        loop = asyncio.get_event_loop()
        self._timer_handle = loop.call_later(OCCUPANCY_TIME, self._turn_off) #120

    def _turn_off(self):
        self._timer_handle = None
        self._update_attribute(OCCUPANCY_STATE, OFF)


class MotionCluster(CustomCluster, IasZone):
    """Motion cluster."""

    cluster_id = IasZone.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._timer_handle = None

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        if command_id == 0:
            if self._timer_handle:
                self._timer_handle.cancel()
            loop = asyncio.get_event_loop()
            self._timer_handle = loop.call_later(MOTION_TIME, self._turn_off)
            self.endpoint.device.occupancy_bus.listener_event(OCCUPANCY_EVENT)

    def _turn_off(self):
        self._timer_handle = None
        self.listener_event(CLUSTER_COMMAND, 999, 0, [0, 0, 0, 0])
        self._update_attribute(ZONE_STATE, OFF)
