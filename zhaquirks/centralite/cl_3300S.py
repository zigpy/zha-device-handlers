"""Device handler for centralite 3300."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import BinaryInput, PowerConfiguration

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

(
    QuirkBuilder(CENTRALITE, "3300")
    # .applies_to(CENTRALITE, "3300-S")  # TODO: this is also defined in `ias.py`!
    .applies_to(CENTRALITE, "3323-G")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .removes(PowerConfiguration.cluster_id, endpoint_id=2)
    .removes(BinaryInput.cluster_id, endpoint_id=2)
    .add_to_registry()
)
