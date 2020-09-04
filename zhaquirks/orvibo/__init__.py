"""Module for ORVIBO quirks implementations."""

from .. import MotionWithReset, OccupancyOnEvent

ORVIBO = "欧瑞博"
ORVIBO_LATIN = "ORVIBO"


class OccupancyCluster(OccupancyOnEvent):
    """Occupancy cluster."""


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    send_occupancy_event: bool = True
