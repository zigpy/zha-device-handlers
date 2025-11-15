"""Device handler for IKEA of Sweden TRADFRI remote control."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.ikea import IKEA, DoublingPowerConfig2CRCluster

# V2 quirks
(
    QuirkBuilder(IKEA, "TRADFRI motion sensor")
    .replaces(DoublingPowerConfig2CRCluster, endpoint_id=1)
    .add_to_registry()
)
