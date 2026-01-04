"""Device handler for smartthings multiV4 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CentraLiteAccelCluster
from zhaquirks.smartthings import SMART_THINGS

(
    QuirkBuilder(SMART_THINGS, "multiv4")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(CentraLiteAccelCluster, endpoint_id=1)
    .add_to_registry()
)
