"""Device handler for Trust ZPIR-8000 sensors."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.trust import MotionCluster

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFFFF


(
    QuirkBuilder("ADUROLIGHT", "VMS_ADUROLIGHT")
    .replaces(replacement_cluster_class=MotionCluster, cluster_id=IasZone.cluster_id)
    .add_to_registry()
)
