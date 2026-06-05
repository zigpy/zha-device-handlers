"""Gledopto GL-C-009P quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

# remove Color cluster so multimode devices don't show color options in ZHA
(
    QuirkBuilder("GLEDOPTO", "GL-C-009P")
    .removes(Color.cluster_id, endpoint_id=11)
    .add_to_registry()
)  # fmt: skip
