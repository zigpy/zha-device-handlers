"""Senoro Window Sensor (TS0601)."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
import zigpy.types as t

from zhaquirks.tuya import BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class OpeningStateEnum(t.enum8):
    """Enum for opening state."""

    Open = 0
    Closed = 1
    Tilted = 2


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
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="opening",
        fallback_name="Opening",
    )
    .skip_configuration()
    .add_to_registry()
)
