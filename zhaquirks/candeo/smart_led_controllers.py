"""Candeo smart led controllers."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.candeo import (
    CANDEO,
    CandeoCCTColorCluster,
    CandeoRGBCCTColorCluster,
    CandeoRGBColorCluster,
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-Dim")
    .applies_to(CANDEO, "C-ZB-LC20-DIM")
    .applies_to(CANDEO, "C-ZB-LC20v2-Dim")
    .applies_to(CANDEO, "C-ZB-LC20v2-DIM")
    .removes(Color.cluster_id, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-CCT")
    .applies_to(CANDEO, "C-ZB-LC20v2-CCT")
    .replaces(CandeoCCTColorCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-RGB")
    .applies_to(CANDEO, "C-ZB-LC20v2-RGB")
    .replaces(CandeoRGBColorCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-RGBCCT")
    .applies_to(CANDEO, "C-ZB-LC20-RGBW")
    .applies_to(CANDEO, "C-ZB-LC20v2-RGBCCT")
    .applies_to(CANDEO, "C-ZB-LC20v2-RGBW")
    .replaces(CandeoRGBCCTColorCluster, endpoint_id=11)
    .add_to_registry()
)
