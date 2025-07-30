"""Nue / 3A Smart Home - Double GPO Quirk."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes
from zigpy.zcl.clusters.lightlink import LightLink

from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


(
    QuirkBuilder("3A Smart Home DE", "LXN56-TS27LX1.2")
    .replaces_endpoint(endpoint_id=1, profile_id=zha.PROFILE_ID, device_type=zha.DeviceType.MAIN_POWER_OUTLET)
    .replaces_endpoint(endpoint_id=2, profile_id=zha.PROFILE_ID, device_type=zha.DeviceType.MAIN_POWER_OUTLET)
    .add_to_registry()
)
