"""GLEDOPTO GL-C-003P quirk.

GLEDOPTO multi-mode LED controllers (GL-C-001P, GL-C-002P, GL-C-201P, GL-C-301P, ...)
report the model GL-C-003P when set to RGB mode. In that mode, the Color cluster
does not advertise XY support in its color capabilities, but ZHA still gets a color
temperature value from it, so ZHA creates a color temperature light without a color
wheel. Report XY support and hide color temperature, so the light is RGB only.
"""

from zigpy.zcl.clusters.lighting import Color

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.gledopto import GLEDOPTO


class GledoptoRGBColorCluster(CustomCluster, Color):
    """Color cluster of a GLEDOPTO controller in RGB mode."""

    _CONSTANT_ATTRIBUTES = {
        Color.AttributeDefs.color_capabilities.id: (
            Color.ColorCapabilities.Hue_and_saturation
            | Color.ColorCapabilities.Enhanced_hue
            | Color.ColorCapabilities.Color_loop
            | Color.ColorCapabilities.XY_attributes
        ),
        Color.AttributeDefs.color_temperature.id: None,
        Color.AttributeDefs.start_up_color_temperature.id: None,
    }


(
    QuirkBuilder(GLEDOPTO, "GL-C-003P")
    .replace_cluster_occurrences(
        GledoptoRGBColorCluster, replace_client_instances=False
    )
    .add_to_registry()
)
