"""Innr SP 242 plug."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import INNR, MeteringClusterInnr

(
    QuirkBuilder(INNR, "SP 242")
    .replaces(MeteringClusterInnr, endpoint_id=1)
    .add_to_registry()
)
