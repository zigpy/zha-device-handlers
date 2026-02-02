"""Tuya TS0601 pilot wire heating control quirk for ZHA - Complete."""
from zigpy.quirks.v2 import EntityPlatform, EntityType
import zigpy.types as t
from zhaquirks.tuya.builder import TuyaQuirkBuilder
class PilotWireMode(t.enum8):
    """Pilot wire mode enum."""
    Comfort = 0x00
    Comfort_Minus_1 = 0x01
    Comfort_Minus_2 = 0x02
    Eco = 0x03
    Anti_Frost = 0x04
    Off = 0x05
class OperatingMode(t.enum8):
    """Operating mode enum."""
    Auto = 0x00
    Manual = 0x01
(
    TuyaQuirkBuilder("_TZE204_3q3maeoo", "TS0601")
    .tuya_enum(
        dp_id=2,
        attribute_name="operating_mode",
        enum_class=OperatingMode,
        translation_key="operating_mode",
        fallback_name="Operating Mode",
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SELECT,
    )
    .tuya_enum(
        dp_id=127,
        attribute_name="pilot_wire_mode",
        enum_class=PilotWireMode,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot Wire Mode",
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SELECT,
    )
    .tuya_temperature(dp_id=16, scale=10)
    .skip_configuration()
    .add_to_registry()
)
