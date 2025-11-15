"""Osram Flex RGBW LED strip."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.osram import OSRAM, OsramLightCluster

(
    QuirkBuilder(OSRAM, "LIGHTIFY Flex RGBW")
    .applies_to(OSRAM, "LIGHTIFY FLEX OUTDOOR RGBW")
    .replaces(OsramLightCluster, endpoint_id=3)
    .add_to_registry()
)
