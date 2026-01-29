"""Device handler for iMagic by Greatstar."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.imagic import IMAGIC

(
    QuirkBuilder(IMAGIC, "1117-S")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)  # fmt: skip
