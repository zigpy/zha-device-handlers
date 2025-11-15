"""Lidl dimmable bulb."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

(
    QuirkBuilder("_TZ3000_nosnx7im", "TS0501A")
    .applies_to("_TZ3000_nbnmw9nc", "TS0501A")
    .applies_to("_TZ3000_7dcddnye", "TS0501A")
    .removes(Color, endpoint_id=1)
    .add_to_registry()
)
