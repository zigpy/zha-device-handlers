"""Quirk for LIDL CCT bulb."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color


class LidlCCTColorCluster(CustomCluster, Color):
    """Lidl CCT Lighting custom cluster."""

    # Remove RGB color wheel for CCT Lighting: only expose color temperature
    # LIDL bulbs do not correctly report this attribute (comes back as None in Home Assistant)
    _CONSTANT_ATTRIBUTES = {0x400A: 16}


(
    QuirkBuilder("_TZ3000_49qchf10", "TS0502A")
    .applies_to("_TZ3000_oborybow", "TS0502A")
    .applies_to("_TZ3000_9evm3otq", "TS0502A")
    .applies_to("_TZ3000_rylaozuc", "TS0502A")
    .applies_to("_TZ3000_el5kt5im", "TS0502A")
    .applies_to("_TZ3000_oh7jddmx", "TS0502A")
    .applies_to("_TZ3000_8uaoilu9", "TS0502A")
    .replaces(LidlCCTColorCluster, endpoint_id=1)
    .add_to_registry()
)
