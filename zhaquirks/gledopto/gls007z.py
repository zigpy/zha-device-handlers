"""GLEDOPTO GL-S-007Z device."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.gledopto import GLEDOPTO

(
    QuirkBuilder(GLEDOPTO, "GL-S-007Z")
    .removes_endpoint(11)
    .removes_endpoint(13)
    .add_to_registry()
)
