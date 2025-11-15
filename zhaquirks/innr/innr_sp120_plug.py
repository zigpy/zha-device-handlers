"""Innr SP 120 plug."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.innr import INNR, ElectricalMeasurementClusterInnr, MeteringClusterInnr

(
    QuirkBuilder(INNR, "SP 120")
    .replaces(ElectricalMeasurementClusterInnr, ElectricalMeasurement, endpoint_id=1)
    .replaces(MeteringClusterInnr, Metering, endpoint_id=1)
    .add_to_registry()
)
