"""Hive Home."""

from zhaquirks import MotionWithReset

HIVEHOME = "HiveHome.com"


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 30
