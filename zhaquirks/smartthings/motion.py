"""Device handler for smartthings motionV4 sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.smartthings import SMART_THINGS

(
    QuirkBuilder(SMART_THINGS, "motionv4")
    .applies_to(SMART_THINGS, "motionv5")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
