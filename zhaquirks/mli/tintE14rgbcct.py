"""Tint E14 RGB CCT."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color


class TintRGBCCTColorCluster(CustomCluster, Color):
    """Tint RGB+CCT Lighting custom cluster."""

    # Set correct capabilities to ct, xy, hs
    # Tint bulbs do not correctly report this attribute
    _CONSTANT_ATTRIBUTES = {0x400A: 0b11110}


(
    QuirkBuilder("MLI", "tint-ExtendedColor")
    .replaces(TintRGBCCTColorCluster, endpoint_id=1)
    .add_to_registry()
)
