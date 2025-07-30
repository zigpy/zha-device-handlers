"""Device handler for hivehome.com MOT003 sensors."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import OccupancySensing, TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.hivehome import HIVEHOME, MotionCluster


(
    QuirkBuilder(HIVEHOME, "MOT003")
    .replaces(replacement_cluster_class=MotionCluster, cluster_id=IasZone.cluster_id, endpoint_id=6)
    .add_to_registry()
)
