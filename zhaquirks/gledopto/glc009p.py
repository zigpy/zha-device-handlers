"""GLEDOPTO GL-C-009P device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

(
    # TODO: this quirk is likely unneeded
    QuirkBuilder("GLEDOPTO", "GL-C-009P")
    .removes(Color, endpoint_id=11)
    .add_to_registry()
)
