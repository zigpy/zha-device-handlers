"""Module for ZHONGXING (knockoff Orvibo) quirks implementations."""

from zhaquirks import LocalDataCluster, MotionWithReset, OccupancyOnEvent

ZHONGXING = "中性"
ZHONGXING_LATIN = "ZHONGXING"


class OccupancyCluster(LocalDataCluster, OccupancyOnEvent):
    """Occupancy cluster."""


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 30
    send_occupancy_event: bool = True
