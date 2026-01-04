"""Tradfri CCT light Quirk."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.ikea import IKEA

# TRADFRI CCT lights with ZHA profile but ZLL device type
(
    QuirkBuilder(IKEA, "TRADFRI bulb GU10 WS 400lm")
    .applies_to(IKEA, "FLOALT panel WS 30x90")
    .applies_to(IKEA, "FLOALT panel WS 60x60")
    .replaces_endpoint(
        1, device_type=zha.DeviceType.COLOR_TEMPERATURE_LIGHT
    )  # was zll.COLOR_TEMPERATURE_LIGHT (0x0220 -> 0x010C)
    .add_to_registry()
)
