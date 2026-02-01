"""Tuya TS0601 pilot wire heating controller quirk for ZHA."""
from zigpy.quirks.v2 import EntityPlatform, EntityType
import zigpy.types as t
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class PilotWireMode(t.enum8):
    """Pilot wire mode enum for French electric radiators."""

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
    # DP 2: Operating mode selector (Auto/Manual)
    .tuya_enum(
        dp_id=2,
        attribute_name="operating_mode",
        enum_class=OperatingMode,
        translation_key="operating_mode",
        fallback_name="Operating Mode",
        entity_type=EntityType.CONFIG,
        entity_platform=EntityPlatform.SELECT,
    )
    # DP 127: Pilot wire mode selector
    .tuya_enum(
        dp_id=127,
        attribute_name="pilot_wire_mode",
        enum_class=PilotWireMode,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot Wire Mode",
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SELECT,
    )
    # DP 16: Local temperature sensor (divided by 10)
    .tuya_temperature(dp_id=16, scale=10)
    # DP 8: Unknown value oscillating between 41-42 (diagnostic)
    .tuya_sensor(
        dp_id=8,
        attribute_name="unknown_dp8",
        type=t.uint8_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="unknown_dp8",
        fallback_name="Unknown DP8",
    )
    # DP 126: Unknown enum value (diagnostic)
    .tuya_sensor(
        dp_id=126,
        attribute_name="unknown_dp126",
        type=t.uint8_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="unknown_dp126",
        fallback_name="Unknown DP126",
    )
    .skip_configuration()
    .add_to_registry()
)
