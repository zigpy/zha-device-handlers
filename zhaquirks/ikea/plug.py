"""IKEA plugs quirk."""
from zigpy.quirks.v2 import add_to_registry_v2
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.ikea import IKEA

# remove LevelControl for plugs to not show config options in ZHA
(
    add_to_registry_v2(IKEA, "TRADFRI control outlet")
    .also_applies_to(IKEA, "TRETAKT Smart plug")
    .removes(LevelControl.cluster_id)
)
