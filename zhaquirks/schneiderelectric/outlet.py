"""Schneider Electric (Wiser) Outlet Quirks."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.schneiderelectric import SE_MANUF_NAME


class MeteringCluster(CustomCluster, Metering):
    """Custom Metering cluster to fix instantaneous demand value multiplied by 1000."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.instantaneous_demand.id:
            value = value / 1000
        super()._update_attribute(attrid, value)


(
    QuirkBuilder(SE_MANUF_NAME, "SOCKET/OUTLET/1")
    .applies_to(SE_MANUF_NAME, "SOCKET/OUTLET/2")
    .replaces(
        replacement_cluster_class=MeteringCluster,
        cluster_id=Metering.cluster_id,
        endpoint_id=6,
    )
    .add_to_registry()
)
