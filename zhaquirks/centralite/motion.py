"""Device handler for centralite motion (only) sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC46  # decimal = 64582
MANUFACTURER_SPECIFIC_PROFILE_ID = 0xC2DF  # decimal = 49887


(
    QuirkBuilder(CENTRALITE, "3305-S")
    .applies_to(CENTRALITE, "3325-S")
    .applies_to(CENTRALITE, "3326-L")
    .replaces(replacement_cluster_class=PowerConfigurationCluster, endpoint_id=1)
    .removes(cluster_id=PowerConfigurationCluster.cluster_id, endpoint_id=2)
    .add_to_registry()
)
