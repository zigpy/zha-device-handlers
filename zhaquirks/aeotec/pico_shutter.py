"""Aeotec Pico Shutter (ZGA004)."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.aeotec.pico_switch import (
    AEOTEC_MANUFACTURER_ID,
    AeotecSwitchActions,
    AeotecSwitchType,
)
from zhaquirks.builder import EntityType, NumberDeviceClass, QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster


class AeotecControls(t.enum8):
    """Whether the external switch can control the covering locally."""

    Disabled = 0x00
    Enabled = 0x01


class AeotecSwitchTypeConfigCluster(CustomCluster):
    """Aeotec switch type configuration cluster [0xFD00].

    Same as the Pico Switch's, plus a Group ID attribute used for the scene
    recall commands sent to bound nodes.
    """

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
        group_id: Final = ZCLAttributeDef(
            id=0x0012,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )


class AeotecOperatingMode(t.enum8):
    """Covering operating mode."""

    Roller_Shade = 0x00  # up/down only, endpoint 2 (tilt) unused
    Shutter = 0x01  # up/down plus slat angle control


class AeotecSlatsReturn(t.enum8):
    """Whether slats return to the previously set tilt position."""

    No_Return = 0x00
    Return_After_Hub = 0x01  # only when activated via the gateway
    Return_After_Any = 0x02  # gateway, ZigBee button, or external switch


class AeotecMovementType(t.enum8):
    """External switch movement behaviour."""

    Momentary = 0x00
    Continuous = 0x01


class AeotecWindowConfigCluster(CustomCluster):
    """Aeotec manufacturer-specific window configuration cluster."""

    cluster_id: t.uint16_t = 0xFD03
    name: str = "Aeotec Window Configuration"
    ep_attribute: str = "aeotec_window_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        operating_mode: Final = ZCLAttributeDef(
            id=0x0001,
            type=AeotecOperatingMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        # units of 0.01 s
        slats_tilt_full_turn_time: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        slats_return: Final = ZCLAttributeDef(
            id=0x0003,
            type=AeotecSlatsReturn,
            zcl_type=DataTypeId.uint8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        # units of 0.01 s
        motor_travel_time: Final = ZCLAttributeDef(
            id=0x0004,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        # units of 1 ms
        momentary_movement_time: Final = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        movement_type: Final = ZCLAttributeDef(
            id=0x0006,
            type=AeotecMovementType,
            zcl_type=DataTypeId.uint8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        # units of 0.01 s
        motor_response_time: Final = ZCLAttributeDef(
            id=0x0007,
            type=t.uint8_t,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )
        limit_verification: Final = ZCLAttributeDef(
            id=0x0008,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        # signals the motor reached a limit during manual calibration
        reach_limit: Final = ZCLCommandDef(
            id=0x00,
            schema={},
            manufacturer_code=AEOTEC_MANUFACTURER_ID,
        )


(
    QuirkBuilder("AEOTEC", "ZGA004")
    .friendly_name(model="Pico Shutter", manufacturer="Aeotec")
    .replaces(AeotecWindowConfigCluster, endpoint_id=1)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=4)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=5)
    .enum(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.operating_mode.name,
        enum_class=AeotecOperatingMode,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="operating_mode",
        fallback_name="Operating mode",
    )
    .enum(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.slats_return.name,
        enum_class=AeotecSlatsReturn,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="slats_return",
        fallback_name="Slat return",
    )
    .enum(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.movement_type.name,
        enum_class=AeotecMovementType,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="movement_type",
        fallback_name="Movement type",
    )
    .number(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.slats_tilt_full_turn_time.name,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        min_value=0,
        max_value=655.35,
        step=0.1,
        multiplier=0.01,  # raw units of 0.01 s
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        translation_key="slats_tilt_full_turn_time",
        fallback_name="Slat tilt full turn time",
    )
    .number(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.motor_travel_time.name,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        min_value=0,
        max_value=655.35,
        step=0.1,
        multiplier=0.01,  # raw units of 0.01 s
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        translation_key="motor_travel_time",
        fallback_name="Motor travel time",
    )
    .number(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.momentary_movement_time.name,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        unit=UnitOfTime.MILLISECONDS,  # raw units of 1 ms
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        translation_key="momentary_movement_time",
        fallback_name="Momentary movement time",
    )
    .number(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.motor_response_time.name,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        min_value=0,
        max_value=2.55,
        step=0.01,
        multiplier=0.01,  # raw units of 0.01 s
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        entity_type=EntityType.CONFIG,
        translation_key="motor_response_time",
        fallback_name="Motor response time",
    )
    .switch(
        attribute_name=AeotecWindowConfigCluster.AttributeDefs.limit_verification.name,
        cluster_id=AeotecWindowConfigCluster.cluster_id,
        entity_type=EntityType.CONFIG,
        translation_key="limit_verification",
        fallback_name="Limit verification",
    )
    # --- External switch S1 (0xFD00, endpoint 4) ---
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        entity_type=EntityType.CONFIG,
        translation_key="s1_switch_type",
        fallback_name="S1 switch type",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        entity_type=EntityType.CONFIG,
        translation_key="s1_switch_actions",
        fallback_name="S1 switch actions",
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        entity_type=EntityType.CONFIG,
        translation_key="s1_local_control",
        fallback_name="S1 local control",
    )
    .number(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.group_id.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=4,
        min_value=1,
        max_value=65527,
        step=1,
        mode="box",
        entity_type=EntityType.CONFIG,
        translation_key="s1_scene_group",
        fallback_name="S1 scene group",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=5,
        entity_type=EntityType.CONFIG,
        translation_key="s2_switch_type",
        fallback_name="S2 switch type",
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=5,
        entity_type=EntityType.CONFIG,
        translation_key="s2_switch_actions",
        fallback_name="S2 switch actions",
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=5,
        entity_type=EntityType.CONFIG,
        translation_key="s2_local_control",
        fallback_name="S2 local control",
    )
    .number(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.group_id.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=5,
        min_value=1,
        max_value=65527,
        step=1,
        mode="box",
        entity_type=EntityType.CONFIG,
        translation_key="s2_scene_group",
        fallback_name="S2 scene group",
    )
    .add_to_registry()
)
