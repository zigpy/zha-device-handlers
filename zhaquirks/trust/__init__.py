"""Trust."""
from .. import MotionWithReset

TRUST = "Trust"


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 30
