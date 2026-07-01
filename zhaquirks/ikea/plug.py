"""IKEA plugs quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.ikea import IKEA

# remove LevelControl for plugs to not show config options in ZHA
(
    QuirkBuilder(IKEA, "TRADFRI control outlet")
    .also_applies_to(IKEA, "TRETAKT Smart plug")
    .also_applies_to(IKEA, "INSPELNING Smart plug")
    .removes(LevelControl.cluster_id)
    .add_to_registry()
)
