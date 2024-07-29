"""Module for Innr quirks implementations."""

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
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


class ElectricalMeasurementClusterInnr(CustomCluster, ElectricalMeasurement):
    """Fix multiplier and divisor for AC current and power."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
    }
