"""Salus KL08RF 8-zone wiring centre (iT600), also sold as Cosmo CFK8L.

The wiring centre drives its zone relays from the reports its thermostats send
it directly, so there is nothing to expose. The quirk keeps it on the network by
answering its sync request, assigning it wiring centre number 1. A wiring centre
keeps the first number it gets; one that holds another number refuses every
zone pairing until it is factory reset.
"""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.salus import (
    COMPUTIME,
    SALUS,
    SalusIt600Basic,
    SalusIt600Cluster,
    SalusIt600Ota,
)

WIRING_CENTRE_ENDPOINT = 8


class SalusKL08Cluster(SalusIt600Cluster):
    """iT600 cluster of the wiring centre."""

    DEFAULT_DEVICE_NUMBER = 1


def is_kl08rf(device) -> bool:
    """Match the wiring centre, which reports no model, by its endpoint."""
    return WIRING_CENTRE_ENDPOINT in device.endpoints


(
    QuirkBuilder(COMPUTIME, None)
    .applies_to(SALUS, None)
    .filter(is_kl08rf)
    .friendly_name(manufacturer="Salus", model="KL08RF")
    # Pinned in case the interview did not get as far as listing the clusters.
    .adds(SalusKL08Cluster, endpoint_id=WIRING_CENTRE_ENDPOINT)
    .adds(SalusIt600Basic, endpoint_id=WIRING_CENTRE_ENDPOINT)
    .replace_cluster_occurrences(SalusKL08Cluster)
    .replace_cluster_occurrences(SalusIt600Basic)
    .replace_cluster_occurrences(SalusIt600Ota)
    .add_to_registry()
)
