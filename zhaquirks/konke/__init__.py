"""Konke sensors."""

import asyncio

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from .. import LocalDataCluster
from ..const import CLUSTER_COMMAND, OFF, ON, ZONE_STATE

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
        self._timer_handle = loop.call_later(OCCUPANCY_TIME, self._turn_off)

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
