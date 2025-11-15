"""Osram tunable white device."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.osram import OSRAM


class OsramColorCluster(CustomCluster, Color):
    """Osram A19 tunable white device."""

    _CONSTANT_ATTRIBUTES = {0x400A: 16, 0x400C: 370}


(
    QuirkBuilder(OSRAM, "LIGHTIFY A19 Tunable White")
    .applies_to(OSRAM, "LIGHTIFY RT Tunable White")
    .replaces(OsramColorCluster, endpoint_id=3)
    .add_to_registry()
)
