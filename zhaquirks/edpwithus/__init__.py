"""EDP WithUs module."""

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.smartenergy import Metering


class MeteringCluster(CustomCluster, Metering):
    """EDP WithUs Metering cluster."""

    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}
