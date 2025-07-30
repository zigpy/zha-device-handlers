"""Module to handle quirks of the  Zen Within thermostat."""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters import general, homeautomation, hvac

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.zen import ZEN, ZenPowerConfiguration


(
    QuirkBuilder(ZEN, "Zen-01")
    .replaces(replacement_cluster_class=ZenPowerConfiguration)
    .add_to_registry()
)
