"""Third Reality switch devices."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.thirdreality import THIRD_REALITY


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


(
    QuirkBuilder(THIRD_REALITY, "3RSS007Z")
    .applies_to(THIRD_REALITY, "3RSS008Z")
    .replaces(CustomPowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
