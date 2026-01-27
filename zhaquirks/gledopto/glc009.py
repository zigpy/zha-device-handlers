"""GLEDOPTO GL-C-009 device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.gledopto import GLEDOPTO

(
	QuirkBuilder(GLEDOPTO, "GL-C-009")
	.removes(Color, endpoint_id=11)
	.add_to_registry()
)  # fmt:skip
