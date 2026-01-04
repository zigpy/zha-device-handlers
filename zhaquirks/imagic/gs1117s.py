"""Device handler for iMagic by Greatstar."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks import PowerConfigurationCluster
from zhaquirks.imagic import IMAGIC

(
    QuirkBuilder(IMAGIC, "1117-S")
    .replaces(
        PowerConfigurationCluster,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=1,
    )
    .add_to_registry()
)
