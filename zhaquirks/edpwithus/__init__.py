"""EDP WithUs module."""
import logging

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.smartenergy import Metering

_LOGGER = logging.getLogger(__name__)


class MeteringCluster(CustomCluster, Metering):
    """EDP WithUs Metering cluster."""

    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}
