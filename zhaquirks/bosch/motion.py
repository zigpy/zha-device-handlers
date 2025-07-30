"""Device handler for Bosch motion sensors."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bosch import BOSCH


class BoschPowerConfiguration(PowerConfigurationCluster):
    """Bosch power configuration cluster for motion sensor."""

    MAX_VOLTS = 3.0
    MIN_VOLTS = 1.9


(
    QuirkBuilder(BOSCH, "ISW-ZPR1-WP13")
    .replaces(replacement_cluster_class=BoschPowerConfiguration, endpoint_id=5)
    .add_to_registry()
)
