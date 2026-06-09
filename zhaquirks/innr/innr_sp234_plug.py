"""Innr SP 234 plug."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import (
    INNR,
    ElectricalMeasurementClusterInnr,
    MeteringClusterInnrOld,
)

(
    QuirkBuilder(INNR, "SP 234")
    .replaces(MeteringClusterInnrOld, endpoint_id=1)
    .replaces(ElectricalMeasurementClusterInnr, endpoint_id=1)
    .add_to_registry()
)
