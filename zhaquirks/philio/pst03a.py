"""Device handler for Philio PST03A-v2.2.5."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    BinaryInput,
    OnOff,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.philio import PHILIO, MotionCluster


(
    QuirkBuilder(PHILIO, "PST03A-v2.2.5")
    .skip_configuration()
    .removes(cluster_id=PowerConfiguration.cluster_id, endpoint_id=1)
    .removes(cluster_id=OccupancySensing.cluster_id, endpoint_id=1)
    .removes(cluster_id=IasZone.cluster_id, endpoint_id=1)
    .removes(cluster_id=OnOff.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(cluster=MotionCluster, endpoint_id=1)
    .adds(cluster=TemperatureMeasurement.cluster_id, endpoint_id=1)
    .adds(cluster=IlluminanceMeasurement.cluster_id, endpoint_id=1)
    .removes(cluster_id=PowerConfiguration.cluster_id, endpoint_id=2)
    .removes(cluster_id=BinaryInput.cluster_id, endpoint_id=2)
    .add_to_registry()
)
