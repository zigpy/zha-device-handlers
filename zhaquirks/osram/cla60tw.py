"""Osram CLA60 TW device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.osram import OSRAM, OsramLightCluster

(
    QuirkBuilder(OSRAM, "CLA60 TW OSRAM")
    .replaces(OsramLightCluster, endpoint_id=3)
    .add_to_registry()
)
