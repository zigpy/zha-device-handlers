"""Innr SP 120 plug."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import (
    INNR,
    ElectricalMeasurementClusterInnr,
    MeteringClusterInnrOld,
)
from zhaquirks.quirk_ids import SE_POLL_SUMMATION

(
    QuirkBuilder(INNR, "SP 120")
    .replaces(MeteringClusterInnrOld)
    .replaces(ElectricalMeasurementClusterInnr)
    .exposes_feature(SE_POLL_SUMMATION)
    .add_to_registry()
)
