"""EDP WithUs module."""

from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.clusters import CustomCluster


class MeteringCluster(CustomCluster, Metering):
    """EDP WithUs Metering cluster."""

    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}
