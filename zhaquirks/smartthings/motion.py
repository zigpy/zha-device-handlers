"""Device handler for smartthings motionV4 sensors."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic, BinaryInput, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.smartthings import SMART_THINGS


(
    QuirkBuilder(SMART_THINGS, "motionv4")
    .applies_to(SMART_THINGS, "motionv5")
    .replaces(PowerConfigurationCluster)
    .add_to_registry()
)
