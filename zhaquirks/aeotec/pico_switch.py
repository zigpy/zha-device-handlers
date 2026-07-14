"""Aeotec Pico Switch (ZGA002)."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster

AEOTEC_MANUFACTURER_ID = 0x1310  # 4880, "AEOTEC LIMITED"


class AeotecSwitchType(t.enum8):
    """External switch type."""

    Toggle = 0x00
    Momentary = 0x01
    Auto_Recognize = 0x04


class AeotecSwitchActions(t.enum8):
    """Mapping of external switch state to the resulting relay action.

    Described as (State 2 press / State 1 release) in the specification.
    """

    On_Off = 0x00
    Off_On = 0x01
    Toggle_Toggle = 0x02


class AeotecControls(t.enum8):
    """Whether the external switch can control the relay locally."""

    Local_Disable = 0x00
    Local_Enable = 0x01


class AeotecSwitchTypeConfigCluster(CustomCluster):
    """Aeotec manufacturer-specific switch type configuration cluster [0xFD00]."""

    cluster_id: t.uint16_t = 0xFD00
    name: str = "Aeotec Switch Type Configuration"
    ep_attribute: str = "aeotec_switch_type_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_type: Final = ZCLAttributeDef(
            id=0x0000,
            type=AeotecSwitchType,
            zcl_type=DataTypeId.enum8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        switch_actions: Final = ZCLAttributeDef(
            id=0x0010,
            type=AeotecSwitchActions,
            zcl_type=DataTypeId.enum8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        controls: Final = ZCLAttributeDef(
            id=0x0011,
            type=AeotecControls,
            zcl_type=DataTypeId.enum8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )


(
    QuirkBuilder("AEOTEC", "ZGA002")
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=2)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=3)
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="s1_switch_type",
        fallback_name="S1 switch type",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="s1_switch_actions",
        fallback_name="S1 switch actions",
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.CONFIG,
        translation_key="s1_local_control",
        fallback_name="S1 local control",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        entity_type=EntityType.CONFIG,
        translation_key="s2_switch_type",
        fallback_name="S2 switch type",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        entity_type=EntityType.CONFIG,
        translation_key="s2_switch_actions",
        fallback_name="S2 switch actions",
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        entity_type=EntityType.CONFIG,
        translation_key="s2_local_control",
        fallback_name="S2 local control",
    )
    .add_to_registry()
)
