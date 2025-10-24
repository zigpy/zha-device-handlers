"""IKEA TRADFRI and TRETAKT plugs quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.ikea import IKEA

# remove LevelControl for plug to not show config options in ZHA
# TRETAKT likely also has Child Lock and LED control, see INSPELNING
(
    QuirkBuilder(IKEA, "TRADFRI control outlet")
    .also_applies_to(IKEA, "TRETAKT Smart plug")
    .removes(LevelControl.cluster_id)
    .add_to_registry()
)
