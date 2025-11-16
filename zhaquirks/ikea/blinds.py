"""Device handler for IKEA of Sweden TRADFRI Fyrtur blinds."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.ikea import IKEA, DoublingPowerConfigClusterIKEA

(
    QuirkBuilder(IKEA, "FYRTUR block-out roller blind")
    .applies_to(IKEA, "KADRILJ roller blind")
    .applies_to(IKEA, "TREDANSEN block-out cellul blind")
    .applies_to(IKEA, "PRAKTLYSING cellular blind")
    .replaces(
        DoublingPowerConfigClusterIKEA,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=1,
    )
    .add_to_registry()
)
