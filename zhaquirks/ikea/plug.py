"""IKEA TRADFRI plugs quirk."""

from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.builder import QuirkBuilder
from zhaquirks.ikea import IKEA

# remove LevelControl for plug to not show config options in ZHA
(
    QuirkBuilder(IKEA, "TRADFRI control outlet")
    .removes(LevelControl.cluster_id)
    .add_to_registry()
)
