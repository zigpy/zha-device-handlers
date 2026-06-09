"""Device handler for GreatStar iMagic 1116-S sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.imagic import IMAGIC

(
    QuirkBuilder(IMAGIC, "1116-S")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
