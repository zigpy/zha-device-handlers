"""Device handler for hivehome.com MOT003 sensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.hivehome import HIVEHOME, MotionCluster

(
    QuirkBuilder(HIVEHOME, "MOT003")
    .replaces(
        replacement_cluster_class=MotionCluster,
        cluster_id=IasZone.cluster_id,
        endpoint_id=6,
    )
    .add_to_registry()
)
