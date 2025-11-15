"""Device handler for centralite ias sensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks import PowerConfigurationCluster

(
    QuirkBuilder("CentraLite", "3300-S")
    .applies_to("CentraLite", "3315-G")
    .applies_to("CentraLite", "3315-L")
    .applies_to("CentraLite", "3315-S")
    .applies_to("CentraLite", "3315-Seu")
    .applies_to("CentraLite", "3315")
    .applies_to("CentraLite", "3320-L")
    .applies_to("CentraLite", "Contact Sensor-A")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .removes(PowerConfiguration.cluster_id, endpoint_id=2)
    .add_to_registry()
)
