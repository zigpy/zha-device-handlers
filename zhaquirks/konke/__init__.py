"""Konke sensors."""

from .. import LocalDataCluster, MotionWithReset, OccupancyOnEvent

KONKE = "Konke"


class OccupancyCluster(LocalDataCluster, OccupancyOnEvent):
    """Occupancy cluster."""

    reset_s: int = 600


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 60
    send_occupancy_event: bool = True
