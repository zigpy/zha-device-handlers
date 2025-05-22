"""Candeo modules."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef, DataTypeId

from zhaquirks.candeo import CANDEO, CandeoSwitchType, CandeoBasicCluster

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
        initially_disabled=False,
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
        initially_disabled=False,
        translation_key="external_switch_type",
        fallback_name="External switch type",
    )
    .add_to_registry()
)
