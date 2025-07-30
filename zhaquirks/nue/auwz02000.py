"""Nue / 3A Smart Home - Double GPO Quirk."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

(
    QuirkBuilder("3A Smart Home DE", "LXN56-TS27LX1.2")
    .replaces_endpoint(
        endpoint_id=1,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.MAIN_POWER_OUTLET,
    )
    .replaces_endpoint(
        endpoint_id=2,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.MAIN_POWER_OUTLET,
    )
    .add_to_registry()
)
