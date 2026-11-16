"""Aeotec Pico Duo Switch (ZGA003)."""

from zhaquirks.aeotec.pico_switch import (
    AeotecSwitchActions,
    AeotecSwitchType,
    AeotecSwitchTypeConfigCluster,
)
from zhaquirks.builder import QuirkBuilder

(
    QuirkBuilder("AEOTEC", "ZGA003")
    .friendly_name(manufacturer="Aeotec", model="Pico Duo Switch")
    # Relays are on endpoints 1 and 2, external switch inputs are on endpoints 3 and 4
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=3)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=4)
    # S1 input
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="switch_type_id",
        fallback_name="S1 switch type",
        translation_placeholders={"id": "S1"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="switch_actions_id",
        fallback_name="S1 switch actions",
        translation_placeholders={"id": "S1"},
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="local_control_id",
        fallback_name="S1 local control",
        translation_placeholders={"id": "S1"},
    )
    # S2 input
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        translation_key="switch_type_id",
        fallback_name="S2 switch type",
        translation_placeholders={"id": "S2"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        translation_key="switch_actions_id",
        fallback_name="S2 switch actions",
        translation_placeholders={"id": "S2"},
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        translation_key="local_control_id",
        fallback_name="S2 local control",
        translation_placeholders={"id": "S2"},
    )
    .add_to_registry()
)
