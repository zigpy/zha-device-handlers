"""Innr SP 240 plug."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.innr import MeteringClusterInnr


class InnrCluster(CustomCluster):
    """Innr manufacturer specific cluster."""

    cluster_id = 0xE001


(
    QuirkBuilder(manufacturer="innr", model="SP 240")
    # Firmware version `421410437` fixed the divisor and multiplier bug
    .firmware_version_filter(max_version=0x191E3685)
    .replaces(MeteringClusterInnr, endpoint_id=1)
    .replaces(InnrCluster, endpoint_id=1)
    .add_to_registry()
)
