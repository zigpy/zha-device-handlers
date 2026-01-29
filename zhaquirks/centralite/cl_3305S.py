"""Device handler for centralite 3305."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

(
    QuirkBuilder(CENTRALITE, "3305-S")
    .applies_to(CENTRALITE, "3305")
    .applies_to(CENTRALITE, "3325-S")
    .applies_to(CENTRALITE, "3325")
    .applies_to(CENTRALITE, "3326-L")
    .applies_to(CENTRALITE, "3326")
    .applies_to(CENTRALITE, "3328-G")
    .applies_to(CENTRALITE, "Motion Sensor-A")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .removes(PowerConfigurationCluster, endpoint_id=2)
    .add_to_registry()
)
