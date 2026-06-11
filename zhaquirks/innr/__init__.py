"""Module for Innr quirks implementations."""

from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

INNR = "innr"


class MeteringClusterInnrOld(CustomCluster, Metering):
    """Provide constant multiplier and divisor for old Innr plug firmware.

    Old firmware provides incorrect values for the divisor, so we override them.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 100,
    }


class MeteringClusterInnrNew(CustomCluster, Metering):
    """Provide constant multiplier and divisor for new Innr plug firmware.

    New firmware provides already provides correct value, but the old quirk will have
    persisted the static values in the database, so we need to force the new values
    to avoid users having to re-pair the device.
    """

    _CONSTANT_ATTRIBUTES = {
        Metering.AttributeDefs.multiplier.id: 1,
        Metering.AttributeDefs.divisor.id: 1000,
    }


class ElectricalMeasurementClusterInnr(CustomCluster, ElectricalMeasurement):
    """Fix multiplier and divisor for AC current and power."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
    }
