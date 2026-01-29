"""Keen Home temperature/humidity/pressure sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Ota, PollControl, Scenes
from zigpy.zcl.clusters.measurement import (
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks.xiaomi import LUMI


class PressureMeasurementCluster(CustomCluster, PressureMeasurement):
    """Custom cluster representing Keen Home's pressure measurement."""

    KEEN_MEASURED_VALUE_ATTR = 0x0020
    MEASURED_VALUE_ATTR = 0x0000

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.KEEN_MEASURED_VALUE_ATTR:
            value = value / 1000.0
            super()._update_attribute(self.MEASURED_VALUE_ATTR, value)


(
    # TODO: is this right??
    QuirkBuilder(LUMI, "RS-THP-MP-1.0")
    .adds(RelativeHumidity, endpoint_id=1)
    .adds(TemperatureMeasurement, endpoint_id=1)
    .replaces(PressureMeasurementCluster, endpoint_id=1)
    .removes(Basic.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .removes(Groups.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .removes(Identify.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .removes(Scenes.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .removes(Ota.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .removes(
        TemperatureMeasurement.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=1,
    )
    .removes(
        RelativeHumidity.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1
    )
    .removes(PollControl.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
