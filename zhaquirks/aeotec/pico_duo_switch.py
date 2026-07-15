"""Aeotec Pico Duo Switch (ZGA003)."""

from zhaquirks.aeotec.pico_switch import (
    AeotecSwitchActions,
    AeotecSwitchType,
    AeotecSwitchTypeConfigCluster,
)
from zhaquirks.builder import EntityType, QuirkBuilder

(
    QuirkBuilder("AEOTEC", "ZGA003")
    .friendly_name(model="Pico Duo Switch", manufacturer="Aeotec")
    # Two relay outputs live on endpoints 1 and 2. 0xFD00 lives on the two
    # scene-controller endpoints, one per external switch input:
    # S1 -> endpoint 3, S2 -> endpoint 4.
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=3)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=4)
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        entity_type=EntityType.CONFIG,
        translation_key="s1_switch_type",
        fallback_name="S1 switch type",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        entity_type=EntityType.CONFIG,
        translation_key="s1_switch_actions",
        fallback_name="S1 switch actions",
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        entity_type=EntityType.CONFIG,
        translation_key="s1_local_control",
        fallback_name="S1 local control",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        entity_type=EntityType.CONFIG,
        translation_key="s2_switch_type",
        fallback_name="S2 switch type",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        entity_type=EntityType.CONFIG,
        translation_key="s2_switch_actions",
        fallback_name="S2 switch actions",
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        entity_type=EntityType.CONFIG,
        translation_key="s2_local_control",
        fallback_name="S2 local control",
    )
    .add_to_registry()
)
