"""Candeo sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.candeo import (
    CANDEO,
    CandeoIasZoneContactCluster,
    CandeoIasZoneMotionCluster,
    CandeoIasZoneWaterCluster,
    CandeoIlluminanceMeasurementCluster,
)

(
    QuirkBuilder(CANDEO, "C-ZB-SEDC")
    .replaces(CandeoIasZoneContactCluster)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-SEMO")
    .replaces(CandeoIasZoneMotionCluster)
    .replaces(CandeoIlluminanceMeasurementCluster)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-SEWA")
    .replaces(CandeoIasZoneWaterCluster)
    .add_to_registry()
)
