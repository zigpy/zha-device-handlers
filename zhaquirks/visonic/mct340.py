"""Visonic MCT340 device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster

OSRAM_DEVICE = 0x0810  # 2064 base 10
OSRAM_CLUSTER = 0xFD00  # 64768 base 10


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


(
    QuirkBuilder("Visonic", "MCT-340 E")
    .applies_to("Visonic", "MCT-340 SMA")
    .replaces(replacement_cluster_class=CustomPowerConfigurationCluster)
    .add_to_registry()
)
