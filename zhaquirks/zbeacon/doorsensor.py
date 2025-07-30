"""Doorsensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PollControl

(
    QuirkBuilder("zbeacon", "DS01")
    .removes(
        cluster_id=PollControl.cluster_id,
        endpoint_id=1,
    )
    .add_to_registry()
)
