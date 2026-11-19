"""Quirk for Adeo ZBEK-1 and ZBEK-4 bulbs."""

from zigpy.device import Device
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import KeepAlive

from zhaquirks.builder import QuirkBuilder


def _missing_keepalive(device: Device) -> bool:
    """Match devices whose endpoint 1 lacks the KeepAlive client."""
    endpoint = device.endpoints.get(1)
    return endpoint is not None and KeepAlive.cluster_id not in endpoint.out_clusters


(
    QuirkBuilder("Adeo", "ZBEK-1")
    .applies_to("Adeo", "ZBEK-4")
    # These bulbs read KeepAlive attributes from the coordinator but may omit
    # the client cluster from their endpoint descriptor.
    .filter(_missing_keepalive)
    .adds(KeepAlive, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
