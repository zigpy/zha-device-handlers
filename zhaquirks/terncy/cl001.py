"""Quirk for Xiaoyan CL001 ceiling light."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color


class ColorClusterTerncy(CustomCluster, Color):
    """Set actual supported CCT range and remove RGB color picker since hardware does not support it."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: Color.ColorCapabilities.Color_temperature,
        Color.AttributeDefs.color_temp_physical_min.id: 50,
        Color.AttributeDefs.color_temp_physical_max.id: 500,
    }


(
    QuirkBuilder("Xiaoyan", "CL001")
    .replaces(ColorClusterTerncy, endpoint_id=1)
    .add_to_registry()
)
