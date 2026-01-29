"""Nue / 3A Smart Home - Double GPO Quirk."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

(
    QuirkBuilder("3A Smart Home DE", "LXN56-TS27LX1.2")
    .replaces_endpoint(
        1, device_type=zha.DeviceType.MAIN_POWER_OUTLET
    )  # Was ON_OFF_LIGHT
    .replaces_endpoint(
        2, device_type=zha.DeviceType.MAIN_POWER_OUTLET
    )  # Was ON_OFF_LIGHT
    .add_to_registry()
)
