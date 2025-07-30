"""Ledvance A19 RGBW device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.ledvance import LEDVANCE, LedvanceLightCluster

(
    QuirkBuilder(LEDVANCE, "A19 RGBW")
    .replaces(
        replacement_cluster_class=LedvanceLightCluster,
        cluster_id=LedvanceLightCluster.cluster_id,
    )
    .add_to_registry()
)
