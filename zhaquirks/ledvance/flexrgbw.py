"""Ledvance flex rgbw device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.ledvance import LEDVANCE, LedvanceLightCluster

(
    QuirkBuilder(LEDVANCE, "FLEX RGBW")
    .replaces(LedvanceLightCluster, endpoint_id=1)
    .add_to_registry()
)
