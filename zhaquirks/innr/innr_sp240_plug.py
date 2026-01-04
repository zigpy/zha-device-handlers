"""Innr SP 240 plug."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import INNR, MeteringClusterInnr


class InnrCluster(CustomCluster):
    """Innr manufacturer specific cluster."""

    cluster_id = 0xE001


(
    QuirkBuilder(INNR, "SP 240")
    .replaces(MeteringClusterInnr, endpoint_id=1)
    .replaces(InnrCluster, endpoint_id=1)
    .add_to_registry()
)
