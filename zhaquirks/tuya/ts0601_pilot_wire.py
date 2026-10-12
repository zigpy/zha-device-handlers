"""Tuya Quirk for support of electric heating pilot wire modules."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class PowernityPOBOCOELECPreset(t.enum8):
    """Enum for preset mode of Powernity PO-BOCO-ELEC pilot wire module."""

    Auto = 0x00
    Manual = 0x01
    Holiday = 0x02


class PowernityPOBOCOELECMode(t.enum8):
    """Enum for mode of Powernity PO-BOCO-ELEC pilot wire module."""

    Off = 0x05
    AntiFrost = 0x04
    Eco = 0x03
    ComfortMinus2 = 0x02
    ComfortMinus1 = 0x01
    Comfort = 0x00


(
    TuyaQuirkBuilder("_TZE204_d6i25bwg", "TS0601")
    .tuya_enum(
        dp_id=2,
        attribute_name="preset",
        enum_class=PowernityPOBOCOELECPreset,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.STANDARD,
        translation_key="preset",
        fallback_name="Preset",
    )
    .tuya_temperature(dp_id=16, scale=10)
    .tuya_humidity(dp_id=8)
    .tuya_enum(
        dp_id=126,
        attribute_name="auto_mode",
        enum_class=PowernityPOBOCOELECMode,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="auto_mode",
        fallback_name="Auto mode",
    )
    .tuya_enum(
        dp_id=127,
        attribute_name="manual_mode",
        enum_class=PowernityPOBOCOELECMode,
        entity_platform=EntityPlatform.SELECT,
        entity_type=EntityType.STANDARD,
        translation_key="manual_mode",
        fallback_name="Manual mode",
    )
    .friendly_name(
        model="PO-BOCO-ELEC",
        manufacturer="Powernity",
    )
    .skip_configuration()
    .add_to_registry()
)
