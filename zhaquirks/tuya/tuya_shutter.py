from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityPlatform, EntityType
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.const import BatterySize
import zigpy.types as t
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTime,
    UnitOfVolume,
)

class OpeningStateEnum(t.enum8):
    """Enum for opening state."""

    Open = 0x00
    Stop = 0x01
    Close = 0x02
    Continue = 0x03

#class SituationSetEnum(t.enum8):
#    """Enum for Situation Set."""
#
#    fully_open = 0
#    fully_close = 1

#class MotorDirectionEnum(t.enum8):
#    """Enum for Motor Direction."""
#
#    Forward = 0
#    Backward = 1

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
    .tuya_number(
        dp_id=2,
        attribute_name="curtain_target_setting",
        type=t.uint32_t,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="curtain_target_setting",
        fallback_name="Curtain Target Setting",
    )
    .tuya_number(
        dp_id=3,
        attribute_name="curtain_postion",
        type=t.uint32_t,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="curtain_position",
        fallback_name="Curtain Position",
    )
    #.tuya_enum(
    #    dp_id=5,
    #    attribute_name="motor_direction",
    #    enum_class=MotorDirectionEnum,
    #    entity_type=EntityType.STANDARD,
    #    entity_platform=EntityPlatform.SENSOR,
    #    translation_key="motor_direction",
    #    fallback_name="Motor Direction",
    #)
    #.tuya_enum(
    #    dp_id=11,
    #    attribute_name="situation_set",
    #    enum_class=SituationSetEnum,
    #    entity_type=EntityType.STANDARD,
    #    entity_platform=EntityPlatform.SENSOR,
    #    translation_key="situation_set",
    #    fallback_name="Situation Set",
    #)
    .tuya_battery(dp_id=13, battery_qty=1)
    #.tuya_switch(
    #    dp_id=101,
    #    attribute_name="child_lock",
    #    translation_key="child_lock",
    #    fallback_name="Child lock",
    #)
    .skip_configuration()
    .add_to_registry()
)

