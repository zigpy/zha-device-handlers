"""Device handler for GreatStar iMagic 1116-S sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.imagic import IMAGIC

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513
MANUFACTURER_SPECIFIC_CLUSTER_ID_2 = 0xFC02  # decimal = 64514


(
    QuirkBuilder(IMAGIC, "1116-S")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
