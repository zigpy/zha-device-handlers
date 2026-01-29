"""Device handler for centralite 3157100."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

(
    QuirkBuilder(CENTRALITE, "3157100")
    .applies_to("Centralite", "3157100")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
