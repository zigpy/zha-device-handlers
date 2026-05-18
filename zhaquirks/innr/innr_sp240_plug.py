"""Innr SP 240 plug."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.innr import MeteringClusterInnrNew, MeteringClusterInnrOld


class InnrCluster(CustomCluster):
    """Innr manufacturer specific cluster."""

    cluster_id = 0xE001


(
    QuirkBuilder(manufacturer="innr", model="SP 240")
    # Firmware version 421410437 fixed the divisor and multiplier bug,
    # so only apply this quirk to versions older than that (max_version is exclusive).
    .firmware_version_filter(max_version=0x191B3685, allow_missing=False)
    .replaces(MeteringClusterInnrOld, endpoint_id=1)
    .replaces(InnrCluster, endpoint_id=1)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=LevelControl.cluster_id)
    .add_to_registry()
)

(
    QuirkBuilder(manufacturer="innr", model="SP 240")
    # Firmware version 421410437 fixed the divisor and multiplier bug,
    # so apply this quirk to that and newer versions to force correct new values,
    # in case the old quirk persisted the old values into the database.
    .firmware_version_filter(min_version=0x191B3685, allow_missing=True)
    .replaces(MeteringClusterInnrNew, endpoint_id=1)
    .replaces(InnrCluster, endpoint_id=1)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=LevelControl.cluster_id)
    .add_to_registry()
)
