"""Module for Bitron/SMaBiT thermostats."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bitron import BITRON
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class Av201032PowerConfigurationCluster(PowerConfigurationCluster):
    """Power configuration cluster for Bitron/SMaBiT AV2010/32 thermostats.

    This cluster takes the reported battery voltage and converts it into a
    battery percentage, since the thermostat does not report this value.
    """

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0


(
    QuirkBuilder(BITRON, "902010/32")
    .replaces(replacement_cluster_class=Av201032PowerConfigurationCluster)
    .add_to_registry()
)
