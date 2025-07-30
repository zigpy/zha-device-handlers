"""Device handler for smartthings multiV4 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CentraLiteAccelCluster
from zhaquirks.smartthings import SMART_THINGS

(
    QuirkBuilder(SMART_THINGS, "multiv4")
    .replaces(
        replacement_cluster_class=PowerConfigurationCluster,
        cluster_id=PowerConfigurationCluster.cluster_id,
        endpoint_id=1,
    )
    .replaces(
        replacement_cluster_class=CentraLiteAccelCluster,
        cluster_id=CentraLiteAccelCluster.cluster_id,
        endpoint_id=1,
    )
    .add_to_registry()
)
