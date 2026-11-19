"""KeepAlive quirk for Adeo ZBEK bulbs."""

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
    .applies_to("Adeo", "ZBEK-2")
    .applies_to("Adeo", "ZBEK-3")
    .applies_to("Adeo", "ZBEK-4")
    .applies_to("Adeo", "ZBEK-5")
    .applies_to("Adeo", "ZBEK-6")
    .applies_to("Adeo", "ZBEK-7")
    .applies_to("Adeo", "ZBEK-8")
    .applies_to("Adeo", "ZBEK-9")
    .applies_to("Adeo", "ZBEK-10")
    .applies_to("Adeo", "ZBEK-11")
    .applies_to("Adeo", "ZBEK-12")
    .applies_to("Adeo", "ZBEK-13")
    .applies_to("Adeo", "ZBEK-14")
    .applies_to("Adeo", "ZBEK-27")
    .applies_to("Adeo", "ZBEK-28")
    .applies_to("Adeo", "ZBEK-29")
    .applies_to("Adeo", "ZBEK-30")
    .applies_to("Adeo", "ZBEK-32")
    .applies_to("Adeo", "ZBEK-33")
    .applies_to("Adeo", "ZBEK-37")
    # These bulbs read KeepAlive attributes from the coordinator but may omit
    # the client cluster from their endpoint descriptor.
    .filter(_missing_keepalive)
    .adds(KeepAlive, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
