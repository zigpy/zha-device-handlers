"""Device handler for centralite motion (only) sensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

(
    QuirkBuilder(CENTRALITE, "3305-S")
    .applies_to(CENTRALITE, "3325-S")
    .applies_to(CENTRALITE, "3326-L")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .removes(PowerConfiguration.cluster_id, endpoint_id=2)
    .add_to_registry()
)
