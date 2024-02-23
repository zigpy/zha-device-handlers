"""Quirks implementations for Schneider Electric devices."""
from typing import Any, Coroutine, Final, Union

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

SE_MANUF_NAME = "Schneider Electric"
SE_MANUF_ID = 4190


class SEBasic(CustomCluster, Basic):
    """Schneider Electric manufacturer specific Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        se_sw_build_id: Final = ZCLAttributeDef(
            id=0xE001,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "002.004.016 R"
        unknown_attribute_57346: Final = ZCLAttributeDef(
            id=0xE002,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "001.000.000"
        unknown_attribute_57348: Final = ZCLAttributeDef(
            id=0xE004,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "213249FEFF5ECFD"
        unknown_attribute_57351: Final = ZCLAttributeDef(
            id=0xE007,
            type=t.enum16,
            is_manufacturer_specific=True,
        )
        se_device_type: Final = ZCLAttributeDef(
            id=0xE008,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "Wiser Light"
        se_model: Final = ZCLAttributeDef(
            id=0xE009,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "NHPB/SHUTTER/1"
        se_realm: Final = ZCLAttributeDef(
            id=0xE00A,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "Wiser Home"
        unknown_attribute_57355: Final = ZCLAttributeDef(
            id=0xE00B,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )  # value: "http://www.schneider-electric.com"


class SEWindowCovering(CustomCluster, WindowCovering):
    """Schneider Electric manufacturer specific Window Covering cluster."""

    class AttributeDefs(WindowCovering.AttributeDefs):
        unknown_attribute_65533: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        lift_duration: Final = ZCLAttributeDef(
            id=0xE000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57360: Final = ZCLAttributeDef(
            id=0xE010,
            type=t.bitmap8,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57362: Final = ZCLAttributeDef(
            id=0xE012,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57363: Final = ZCLAttributeDef(
            id=0xE013,
            type=t.bitmap8,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57364: Final = ZCLAttributeDef(
            id=0xE014,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57365: Final = ZCLAttributeDef(
            id=0xE015,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57366: Final = ZCLAttributeDef(
            id=0xE016,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_57367: Final = ZCLAttributeDef(
            id=0xE017,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid: Union[int, t.uint16_t], value: Any):
        if attrid == WindowCovering.AttributeDefs.current_position_lift_percentage.id:
            # Invert the percentage value
            value = 100 - value
        super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args: Any,
        **kwargs: Any,
    ) -> Coroutine:
        command = self.server_commands[command_id]

        # Override default command to invert percent lift value.
        if command.id == WindowCovering.ServerCommandDefs.go_to_lift_percentage.id:
            percent = args[0]
            percent = 100 - percent
            return await super().command(command_id, percent, **kwargs)

        return await super().command(command_id, *args, **kwargs)


class SELedIndicatorSignals(t.enum8):
    """Available LED indicator signal combinations.

    Shutter movement can be indicated with a red LED signal. A green LED
    light permanently provides orientation, if desired.
    """

    MOVEMENT_ONLY = 0x00
    MOVEMENT_AND_ORIENTATION = 0x01
    ORIENTATION_ONLY = 0x02
    NONE = 0x03


class SESpecific(CustomCluster):
    """Schneider Electric manufacturer specific cluster."""

    name = "Schneider Electric Manufacturer Specific"
    ep_attribute = "schneider_electric_manufacturer"
    cluster_id = 0xFF17

    class AttributeDefs(BaseAttributeDefs):
        led_indicator_signals: Final = ZCLAttributeDef(
            id=0x0000,
            type=SELedIndicatorSignals,
            is_manufacturer_specific=True,
        )
        unknown_attribute_1: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.enum8,
            is_manufacturer_specific=True,
        )
        unknown_attribute_16: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_17: Final = ZCLAttributeDef(
            id=0x0011,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_32: Final = ZCLAttributeDef(
            id=0x0020,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_33: Final = ZCLAttributeDef(
            id=0x0021,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        unknown_attribute_65533: Final = ZCLAttributeDef(
            id=0xFFFD,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
