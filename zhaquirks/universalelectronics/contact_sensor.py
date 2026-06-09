"""XHS2-UE Door/Window Sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


(
    QuirkBuilder("Universal Electronics Inc", "URC4460BC0-X-R")
    .replaces(CustomPowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
