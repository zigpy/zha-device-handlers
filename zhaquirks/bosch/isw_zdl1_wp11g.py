"""Device handler for Bosch ISWZDL1WP11G motion sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bosch import BOSCH


class BoschWP11GPowerConfiguration(PowerConfigurationCluster):
    """Bosch power configuration cluster for ISWZDL1WP11G motion sensor."""

    MAX_VOLTS = 6.0
    MIN_VOLTS = 3.0


(
    QuirkBuilder(BOSCH, "ISW-ZDL1-WP11G")
    .replaces(BoschWP11GPowerConfiguration, endpoint_id=5)
    .add_to_registry()
)
