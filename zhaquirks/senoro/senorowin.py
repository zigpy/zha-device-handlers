from zigpy.quirks.v2.homeassistant import EntityType, EntityPlatform
import zigpy.types as t
from zhaquirks.tuya import BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class OpeningStateEnum(t.enum8):
    open = 0
    closed = 1
    tilted = 2


(
    TuyaQuirkBuilder("_TZE200_ytx9fudw", "TS0601")
    .tuya_battery(
        dp_id=2,
        battery_type=BatterySize.CR2032,
        battery_qty=3,
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="opening_state",
        enum_class=OpeningStateEnum,
        translation_key="opening_state",
        fallback_name="Opening state",
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="alarm",
        entity_type=EntityType.STANDARD,
        translation_key="alarm",
        fallback_name="Tamper Alarm",
    )
    .skip_configuration()
    .add_to_registry()
)
