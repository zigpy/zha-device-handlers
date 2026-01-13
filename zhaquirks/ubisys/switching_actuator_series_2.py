"""Ubisys Switching Actuator S1 quirk."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.quirk_ids import SE_POLL_SUMMATION


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 10,
    }


(
    QuirkBuilder(manufacturer="ubisys", model="S1 (5501)")
    .replaces(UbisysElectricalMeasurement, endpoint_id=3)
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .add_to_registry()
)
