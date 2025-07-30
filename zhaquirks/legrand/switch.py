"""Module for Legrand switches (without dimming functionality)."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.legrand import LEGRAND, MANUFACTURER_SPECIFIC_CLUSTER_ID, LegrandCluster

(
    QuirkBuilder(f" {LEGRAND}", " Light switch with neutral")
    .replaces(
        replacement_cluster_class=LegrandCluster,
        cluster_id=MANUFACTURER_SPECIFIC_CLUSTER_ID,
        endpoint_id=1,
    )
    .add_to_registry()
)
