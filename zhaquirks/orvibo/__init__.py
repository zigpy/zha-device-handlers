"""Module for ORVIBO quirks implementations."""

from .. import MotionWithReset, OccupancyOnEvent

ORVIBO = "欧瑞博"
ORVIBO_LATIN = "ORVIBO"


class OccupancyCluster(OccupancyOnEvent):
    """Occupancy cluster."""


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 30
    send_occupancy_event: bool = True
