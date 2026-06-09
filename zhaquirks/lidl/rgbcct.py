"""Quirk for LIDL RGB+CCT bulb."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color


class LidlRGBCCTColorCluster(CustomCluster, Color):
    """Lidl RGB+CCT Lighting custom cluster."""

    # Set correct capabilities to ct, xy, hs
    # LIDL bulbs do not correctly report this attribute (comes back as None in Home Assistant)
    _CONSTANT_ATTRIBUTES = {0x400A: 0b11001}


(
    QuirkBuilder("_TZ3000_dbou1ap4", "TS0505A")
    .replaces(LidlRGBCCTColorCluster, endpoint_id=1)
    .add_to_registry()
)
