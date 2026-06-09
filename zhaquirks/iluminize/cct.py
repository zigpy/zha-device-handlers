"""Quirk for iluminize CCT actor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.iluminize import ILUMINIZE


class IluminizeCCTColorCluster(CustomCluster, Color):
    """iluminize CCT Lighting custom cluster."""

    # Remove RGB color wheel for CCT Lighting: only expose color temperature
    _CONSTANT_ATTRIBUTES = {0x400A: 16}


(
    QuirkBuilder(ILUMINIZE, "CCT Lighting")
    .replaces(IluminizeCCTColorCluster, endpoint_id=1)
    .add_to_registry()
)
