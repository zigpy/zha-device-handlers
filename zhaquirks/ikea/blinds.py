"""Device handler for IKEA of Sweden TRADFRI Fyrtur blinds."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.ikea import IKEA, DoublingPowerConfigClusterIKEA

(
    QuirkBuilder(IKEA, "FYRTUR block-out roller blind")
    .applies_to(IKEA, "KADRILJ roller blind")
    .applies_to(IKEA, "TREDANSEN block-out cellul blind")
    .applies_to(IKEA, "PRAKTLYSING cellular blind")
    .replaces(DoublingPowerConfigClusterIKEA, endpoint_id=1)
    .add_to_registry()
)
