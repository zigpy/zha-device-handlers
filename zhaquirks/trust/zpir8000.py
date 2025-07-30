"""Device handler for Trust ZPIR-8000 sensors."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.trust import MotionCluster

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFFFF


(
    QuirkBuilder("ADUROLIGHT", "VMS_ADUROLIGHT")
    .replaces(replacement_cluster_class=MotionCluster, cluster_id=IasZone.cluster_id)
    .add_to_registry()
)
