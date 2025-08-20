"""Tuya Plantation Shutter."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import PERCENTAGE
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class OpeningStateEnum(t.enum8):
    """Enum for opening state."""

    Open = 0x00
    Stop = 0x01
    Close = 0x02
    Continue = 0x03


class SituationSetEnum(t.enum8):
    """Enum for Situation Set."""

    fully_open = 0x00
    fully_close = 0x01


class MotorDirectionEnum(t.enum8):
    """Enum for Motor Direction."""

    Forward = 0x00
    Backward = 0x01


class BorderLimitEnum(t.enum8):
    """Enum for Border Limit Setting."""

    up = 0x00
    down = 0x01
    up_delete = 0x02
    down_delete = 0x03
    remove_top_bottom = 0x04


(
    TuyaQuirkBuilder("_TZE284_myikb7qz", "TS0601")
    .tuya_enum(
        dp_id=1,
        attribute_name="control_state",
        enum_class=OpeningStateEnum,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="control",
        fallback_name="Control",
    )
    # Working
    .tuya_number(
        dp_id=2,
        attribute_name="shutter_target_setting",
        type=t.uint32_t,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="shutter_target_setting",
        fallback_name="Shutter Target Setting",
    )
    # Working
    .tuya_number(
        dp_id=3,
        attribute_name="shutter_postion",
        type=t.uint32_t,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="shutter_position",
        fallback_name="Shutter Position",
    )
    # Working Needs to be manually triggered to pick up sensor
    .tuya_enum(
        dp_id=5,
        attribute_name="motor_direction",
        enum_class=MotorDirectionEnum,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="motor_direction",
        fallback_name="Motor Direction",
    )
    # Not Working
    .tuya_enum(
        dp_id=11,
        attribute_name="situation_set",
        enum_class=SituationSetEnum,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="situation_set",
        fallback_name="Situation Set",
    )
    # power_cfg=PowerConfiguration does not work
    .tuya_battery(
        dp_id=13,
    )
    # Not working
    .tuya_enum(
        dp_id=16,
        attribute_name="border_limit",
        enum_class=BorderLimitEnum,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="border_limit",
        fallback_name="Border Limit Setting",
    )
    # Not working
    .tuya_number(
        dp_id=19,
        attribute_name="position_best",
        type=t.uint32_t,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="position_best",
        fallback_name="Best Position",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .skip_configuration()
    .add_to_registry()
)
