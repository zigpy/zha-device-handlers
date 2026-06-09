"""Osram Smart+ AC05347 GU10 White."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.osram import OSRAM, OsramLightCluster

(
    QuirkBuilder(OSRAM, "Smart+ AC05347")
    .replaces(OsramLightCluster, endpoint_id=3)
    .add_to_registry()
)
