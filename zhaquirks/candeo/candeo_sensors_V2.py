"""Candeo sensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Identify

from zhaquirks.candeo import (
    CANDEO,
    CandeoIasZoneContactCluster,
    CandeoIasZoneMotionCluster,
    CandeoIasZoneWaterCluster,
    CandeoIlluminanceMeasurementCluster,
)

base_quirk = QuirkBuilder().removes(Identify.cluster_id)

(
    base_quirk.clone()
    .applies_to(CANDEO, "C-ZB-SEDC")
    .replaces(CandeoIasZoneContactCluster)
    .add_to_registry()
)

(
    base_quirk.clone()
    .applies_to(CANDEO, "C-ZB-SEMO")
    .replaces(CandeoIasZoneMotionCluster)
    .replaces(CandeoIlluminanceMeasurementCluster)
    .add_to_registry()
)

(
    base_quirk.clone()
    .applies_to(CANDEO, "C-ZB-SEWA")
    .replaces(CandeoIasZoneWaterCluster)
    .add_to_registry()
)

(base_quirk.clone().applies_to(CANDEO, "C-ZB-SETE").add_to_registry())
