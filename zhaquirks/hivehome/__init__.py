"""Hive Home."""
import asyncio

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.security import IasZone

ON = 1
OFF = 0
ZONE_STATE = 0


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
            self._timer_handle = loop.call_later(30, self._turn_off)

    def _turn_off(self):
        self._timer_handle = None
        self.listener_event('cluster_command', 999, 0, [
            0, 0, 0, 0
        ])
        self._update_attribute(ZONE_STATE, OFF)
