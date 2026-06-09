"""Osram LIGHTIFY A19 RGBW device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.osram import OSRAM, OsramLightCluster

(
    QuirkBuilder(OSRAM, "LIGHTIFY A19 RGBW")
    .replaces(OsramLightCluster, endpoint_id=3)
    .add_to_registry()
)
