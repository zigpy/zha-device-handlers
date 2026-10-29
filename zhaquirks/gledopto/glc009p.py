"""Gledopto GL-C-009P quirk."""

from zigpy.zcl.clusters.lighting import Color

from zhaquirks.builder import QuirkBuilder

# The GL-C-009P is a single-color dimmer that still announces the Color cluster.
# Remove it so ZHA doesn't show color temperature controls. Depending on the
# firmware, the light is on endpoint 1 (with Green Power endpoint 242) or 11.
(
    QuirkBuilder("GLEDOPTO", "GL-C-009P")
    .filter(lambda device: 1 in device.endpoints)
    .removes(Color.cluster_id, endpoint_id=1)
    .add_to_registry()
)

(
    QuirkBuilder("GLEDOPTO", "GL-C-009P")
    .filter(lambda device: 11 in device.endpoints)
    .removes(Color.cluster_id, endpoint_id=11)
    .add_to_registry()
)
