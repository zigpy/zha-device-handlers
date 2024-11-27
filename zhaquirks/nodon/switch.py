"""NodOn on/off switch two channels."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

NODON = "NodOn"

(
    # this quirk is a v2 version of 7397b6a
    QuirkBuilder(NODON, "SIN-4-2-20")
    .removes(cluster_id=LevelControl.cluster_id, endpoint_id=1)
    .removes(cluster_id=LevelControl.cluster_id, endpoint_id=2)
    .add_to_registry()
)
