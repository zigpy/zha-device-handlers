"""Module for Innr quirks implementations."""
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.smartenergy import Metering

INNR = "innr"


class MeteringClusterInnr(CustomCluster, Metering):
    """Provide constant multiplier and divisor.

    The device seems to supply the summation_formatting attribute correctly, but ZHA doesn't use it for kWh for now.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }
