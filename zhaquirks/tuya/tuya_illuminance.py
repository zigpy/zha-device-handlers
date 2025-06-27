"""Tuya illuminance sensors."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.types import t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class BrightnessLevel(t.enum8):
    """Brightness level enum."""

    Low = 0x00
    Medium = 0x01
    High = 0x02
    Strong = 0x03


(
    TuyaQuirkBuilder("_TZE200_khx7nnka", "TS0601")  # Tuya XFY-CGQ-ZIGB
    .applies_to("_TZE204_khx7nnka", "TS0601")
    .applies_to("_TZE200_yi4jtqq1", "TS0601")
    .tuya_enum(
        dp_id=1,
        attribute_name="brightness_level",
        enum_class=BrightnessLevel,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="brightness_level",
        fallback_name="Brightness level",
    )
    .tuya_illuminance(dp_id=2)
    .skip_configuration()
    .add_to_registry()
)
