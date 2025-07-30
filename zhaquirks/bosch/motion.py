"""Device handler for Bosch motion sensors."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.bosch import BOSCH
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class BoschPowerConfiguration(PowerConfigurationCluster):
    """Bosch power configuration cluster for motion sensor."""

    MAX_VOLTS = 3.0
    MIN_VOLTS = 1.9


(
    QuirkBuilder(BOSCH, "ISW-ZPR1-WP13")
    .replaces(replacement_cluster_class=BoschPowerConfiguration, endpoint_id=5)
    .add_to_registry()
)
