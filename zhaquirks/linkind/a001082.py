"""Linkind A001082 Leak Sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.linkind import LinkindBasicCluster

(
    QuirkBuilder("LK", "A001082")
    .replaces(LinkindBasicCluster, endpoint_id=1)
    .add_to_registry()
)
