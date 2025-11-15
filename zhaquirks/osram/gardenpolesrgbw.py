"""Osram RGBW Gardenpoles."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.osram import OSRAM, OsramLightCluster

(
    QuirkBuilder(OSRAM, "Gardenpole RGBW-Lightify")
    .replaces(OsramLightCluster, endpoint_id=1)
    .add_to_registry()
)
