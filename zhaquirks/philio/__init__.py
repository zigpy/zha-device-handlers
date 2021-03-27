"""Module for Philio quirks implementations."""

from zhaquirks import MotionWithReset

PHILIO = "Philio"


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 30
