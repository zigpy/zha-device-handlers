"""Ubisys Switching Actuator S1-R (Series 2) quirk."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 10,
    }


(
    QuirkBuilder(manufacturer="ubisys", model="S1-R (5601)")
    .replaces(UbisysElectricalMeasurement)
    .add_to_registry()
)
