"""Gledopto GL-C-009P quirk."""

from zigpy.zcl.clusters.lighting import Color

from zhaquirks.builder import QuirkBuilder

# remove Color cluster so multimode devices don't show color options in ZHA
(
    QuirkBuilder("GLEDOPTO", "GL-C-009P")
    .removes(Color.cluster_id, endpoint_id=11)
    .add_to_registry()
)  # fmt: skip
