"""Tuya TS0601 pilot wire (fil pilote) heating controller.

Tested with:
  - _TZE204_3q3maeoo TS0601 (6-mode French pilot wire controller)

The French "fil pilote" standard defines up to 6 heating modes sent over a
dedicated wire using AC phase modulation. This controller bridges Zigbee to
that standard.

Observed data points:
  DP  2  - Operating mode (Auto / Manual)
  DP 16  - Current temperature in 0.1 °C (e.g. 205 → 20.5 °C)
  DP 127 - Pilot wire mode (6 modes: Comfort, Comfort-1, Comfort-2, Eco,
            Anti-frost, Off)
"""

import zigpy.types as t
from zigpy.quirks.v2 import EntityPlatform, EntityType

from zhaquirks.tuya.builder import TuyaQuirkBuilder


class OperatingMode(t.enum8):
    """Operating mode: automatic schedule vs. manual override."""

    Auto = 0x00
    Manual = 0x01


class PilotWireMode(t.enum8):
    """French fil pilote 6-mode heating setpoint."""

    Comfort = 0x00
    Comfort_minus_1 = 0x01
    Comfort_minus_2 = 0x02
    Eco = 0x03
    Anti_frost = 0x04
    Off = 0x05


(
    TuyaQuirkBuilder("_TZE204_3q3maeoo", "TS0601")
    .tuya_enum(
        dp_id=2,
        attribute_name="operating_mode",
        enum_class=OperatingMode,
        translation_key="operating_mode",
        fallback_name="Operating Mode",
        entity_type=EntityType.CONFIG,
        entity_platform=EntityPlatform.SELECT,
    )
    .tuya_temperature(dp_id=16, scale=10)
    .tuya_enum(
        dp_id=127,
        attribute_name="pilot_wire_mode",
        enum_class=PilotWireMode,
        translation_key="pilot_wire_mode",
        fallback_name="Pilot Wire Mode",
        entity_type=EntityType.CONFIG,
        entity_platform=EntityPlatform.SELECT,
    )
    .tuya_sensor(
        dp_id=8,
        attribute_name="dp8_unknown",
        type=t.uint8_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="dp8_unknown",
        fallback_name="DP8 (unknown)",
    )
    .tuya_sensor(
        dp_id=126,
        attribute_name="dp126_unknown",
        type=t.uint8_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="dp126_unknown",
        fallback_name="DP126 (unknown)",
    )
    .skip_configuration()
    .add_to_registry()
)
