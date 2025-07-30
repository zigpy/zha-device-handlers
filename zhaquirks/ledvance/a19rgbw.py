"""Ledvance A19 RGBW device."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ledvance import LEDVANCE, LedvanceLightCluster


(
    QuirkBuilder(LEDVANCE, "A19 RGBW")
    .replaces(replacement_cluster_class=LedvanceLightCluster, cluster_id=LedvanceLightCluster.cluster_id)
    .add_to_registry()
)
