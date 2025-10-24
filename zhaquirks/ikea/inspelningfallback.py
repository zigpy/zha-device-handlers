"""IKEA INSPELNING plug quirk (old firmware fallback)."""
# It is unclear if the fw version before 0x02040045 / 2.4.45 already had access
# to the child lock and LED attributes.

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.ikea import IKEA

# remove LevelControl for plug to not show config options in ZHA
# firmware max_version is exclusive
(
    QuirkBuilder(IKEA, "INSPELNING Smart plug")
    .firmware_version_filter(max_version=0x02040045, allow_missing=False)
    .removes(LevelControl.cluster_id)
    .add_to_registry()
)
