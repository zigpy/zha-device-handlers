"""Samjin Multi 2019 Refresh Quirk."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.samjin import SAMJIN
from zhaquirks.smartthings import SmartThingsAccelCluster

(
    QuirkBuilder(SAMJIN, "multi")
    .replaces(SmartThingsAccelCluster, endpoint_id=1)
    .add_to_registry()
)
