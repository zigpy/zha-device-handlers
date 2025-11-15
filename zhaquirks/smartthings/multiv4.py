"""Device handler for smartthings multiV4 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CentraLiteAccelCluster
from zhaquirks.smartthings import SMART_THINGS

(
    QuirkBuilder(SMART_THINGS, "multiv4")
    .replaces(PowerConfigurationCluster)
    .replaces(CentraLiteAccelCluster)
    .add_to_registry()
)
