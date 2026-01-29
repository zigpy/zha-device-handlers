"""Module for Bitron/SMaBiT thermostats."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bitron import BITRON


class Av201032PowerConfigurationCluster(PowerConfigurationCluster):
    """Power configuration cluster for Bitron/SMaBiT AV2010/32 thermostats.

    This cluster takes the reported battery voltage and converts it into a
    battery percentage, since the thermostat does not report this value.
    """

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0


(
    QuirkBuilder(BITRON, "902010/32")
    .replaces(Av201032PowerConfigurationCluster, endpoint_id=1)
    .add_to_registry()
)
