"""Device handler for Philio PST03A-v2.2.5."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.philio import MotionCluster

(
    # TODO: is this correct? The v1 quirk had no manufacturer name.
    QuirkBuilder("Philio", "PST03A-v2.2.5")
    .skip_configuration()
    .replaces(MotionCluster, endpoint_id=1)
    .removes(PowerConfiguration, endpoint_id=1)
    .removes(OccupancySensing, endpoint_id=1)
    .removes(IasZone, endpoint_id=1)
    .removes(OnOff, endpoint_id=1, cluster_type=ClusterType.Client)
    .adds(TemperatureMeasurement, endpoint_id=1)
    .adds(IlluminanceMeasurement, endpoint_id=1)
    .removes(PowerConfiguration, endpoint_id=2)
    .removes(BinaryInput, endpoint_id=2)
    .add_to_registry()
)
