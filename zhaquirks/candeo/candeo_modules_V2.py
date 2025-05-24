"""Candeo modules."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.candeo import CANDEO, CandeoBasicCluster, CandeoSwitchType

(
    QuirkBuilder(CANDEO, "C203")
    .applies_to(CANDEO, "HK-LN-DIM-A")
    .applies_to(CANDEO, "C204")
    .applies_to(CANDEO, "C-ZB-DM204")
    .applies_to(CANDEO, "C205")
    .replaces(CandeoBasicCluster)
    .enum(
        attribute_name=CandeoBasicCluster.AttributeDefs.external_switch_type.name,
        enum_class=CandeoSwitchType,
        cluster_id=CandeoBasicCluster.cluster_id,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
)

(
    QuirkBuilder(CANDEO, "C-ZB-SM205-2G")
    .replaces(CandeoBasicCluster, endpoint_id=11)
    .enum(
        attribute_name=CandeoBasicCluster.AttributeDefs.external_switch_type.name,
        enum_class=CandeoSwitchType,
        cluster_id=CandeoBasicCluster.cluster_id,
        endpoint_id=11,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
)
