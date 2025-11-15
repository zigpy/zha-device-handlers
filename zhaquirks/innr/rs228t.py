"""Innr RS 228 T device."""

from zigpy.profiles.zha import DeviceType
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import INNR

(
    QuirkBuilder(INNR, "RS 228 T")
    # Was COLOR_TEMPERATURE_LIGHT
    .replaces_endpoint(1, device_type=DeviceType.COLOR_DIMMABLE_LIGHT)
    .add_to_registry()
)
