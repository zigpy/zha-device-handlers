"""Device handler for centralite 3305."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE

#  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
#  device_version=0
#  input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
#  output_clusters=[25]>
#  <SimpleDescriptor endpoint=2 profile=260 device_type=263
#  device_version=0
#  input_clusters=[0, 1, 3, 1030, 2821]
#  output_clusters=[3]>
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

(
    QuirkBuilder(CENTRALITE, "3305")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .skip_configuration()
    .add_to_registry()
)
