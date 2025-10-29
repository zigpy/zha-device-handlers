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
    .removes(Color.cluster_id, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-CCT")
    .replaces(CandeoCCTColorCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-RGB")
    .replaces(CandeoRGBColorCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-LC20-RGBCCT")
    .applies_to(CANDEO, "C-ZB-LC20-RGBW")
    .replaces(CandeoRGBCCTColorCluster, endpoint_id=11)
    .add_to_registry()
)
