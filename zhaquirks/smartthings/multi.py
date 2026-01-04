"""Smart Things multi purpose sensor quirk."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.smartthings import SMART_THINGS, SmartThingsAccelCluster

(
    QuirkBuilder(SMART_THINGS, "multi")
    .replaces(SmartThingsAccelCluster, endpoint_id=1)
    .add_to_registry()
)
