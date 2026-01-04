"""Innr SP 120 plug."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import INNR, ElectricalMeasurementClusterInnr, MeteringClusterInnr

(
    QuirkBuilder(INNR, "SP 120")
    .replaces(ElectricalMeasurementClusterInnr, endpoint_id=1)
    .replaces(MeteringClusterInnr, endpoint_id=1)
    .add_to_registry()
)
