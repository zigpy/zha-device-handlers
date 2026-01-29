"""Quirk for iluminize DIM actor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.iluminize import ILUMINIZE


class IluminizeDIMColorCluster(CustomCluster, Color):
    """iluminize DIM Lighting custom cluster."""

    # Remove RGB color wheel for DIM Lighting
    _CONSTANT_ATTRIBUTES = {0x400A: 0}


(
    QuirkBuilder(ILUMINIZE, "DIM Lighting")
    .replaces(IluminizeDIMColorCluster, endpoint_id=1)
    .add_to_registry()
)
