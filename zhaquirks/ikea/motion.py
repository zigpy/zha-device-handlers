"""Device handler for IKEA of Sweden TRADFRI remote control."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.ikea import IKEA, DoublingPowerConfig2CRCluster

(
    QuirkBuilder(IKEA, "TRADFRI motion sensor")
    .replaces(
        DoublingPowerConfig2CRCluster, PowerConfiguration.cluster_id, endpoint_id=1
    )
    .add_to_registry()
)
