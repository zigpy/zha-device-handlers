"""Salus SP600 plug."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.salus import COMPUTIME


class TemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """Temperature cluster that divides value by 2."""

    ATTR_ID = 0

    def _update_attribute(self, attrid, value):
        # divide values by 2
        if attrid == self.ATTR_ID:
            value = value / 2
        super()._update_attribute(attrid, value)


(
    QuirkBuilder(COMPUTIME, "SP600")
    .applies_to(COMPUTIME, "SPE600")
    .replaces(TemperatureMeasurementCluster, endpoint_id=9)
    .add_to_registry()
)
