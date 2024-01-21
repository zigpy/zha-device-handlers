from typing import Any, Coroutine, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef


class SEBasic(CustomCluster, Basic):
    """Schneider Electric manufacturer specific Basic cluster."""

    attributes: dict[int, ZCLAttributeDef] = Basic.attributes.copy()

    attributes.update(
        {
            0xE001: (
                "se_sw_build_id",
                t.CharacterString,
                True,
            ),  # value: "002.004.016 R
            0xE002: (
                "unknown_attribute_57346",
                t.CharacterString,
                True,
            ),  # value: "001.000.000"
            0xE004: (
                "unknown_attribute_57348",
                t.CharacterString,
                True,
            ),  # value: "213249FEFF5ECFD"
            0xE007: (
                "unknown_attribute_57351",
                t.enum16,
                True,
            ),
            0xE008: (
                "se_device_type",
                t.CharacterString,
                True,
            ),  # value: "Wiser Light"
            0xE009: (
                "se_model",
                t.CharacterString,
                True,
            ),  # value: "NHPB/SHUTTER/1"
            0xE00A: (
                "se_realm",
                t.CharacterString,
                True,
            ),  # value: "Wiser Home"
            0xE00B: (
                "unknown_attribute_57355",
                t.CharacterString,
                True,
            ),  # value: "http://www.schneider-electric.com"
        }
    )


class SEWindowCovering(CustomCluster, WindowCovering):
    """Schneider Electric manufacturer specific Window Covering cluster."""

    attributes: dict[int, ZCLAttributeDef] = WindowCovering.attributes.copy()

    attributes.update(
        {
            0xFFFD: ("unknown_attribute_65533", t.uint16_t, True),
            0xE000: ("lift_duration", t.uint16_t, True),
            0xE010: ("unknown_attribute_57360", t.bitmap8, True),
            0xE012: ("unknown_attribute_57362", t.uint16_t, True),
            0xE013: ("unknown_attribute_57363", t.bitmap8, True),
            0xE014: ("unknown_attribute_57364", t.uint16_t, True),
            0xE015: ("unknown_attribute_57365", t.uint16_t, True),
            0xE016: ("unknown_attribute_57366", t.uint16_t, True),
            0xE017: ("unknown_attribute_57367", t.uint8_t, True),
        }
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


class SESpecific(CustomCluster):
    """Schneider Electric manufacturer specific cluster."""

    name = "Schneider Electric Manufacturer Specific"
    ep_attribute = "schneider_electric_manufacturer"
    cluster_id = 0xFF17

    class LedIndicatorSignals(t.enum8):
        """Available LED indicator signal combinations.

        Shutter movement can be indicated with a red LED signal. A green LED
        light permanently provides orientation, if desired.
        """

        MOVEMENT_ONLY = 0x00
        MOVEMENT_AND_ORIENTATION = 0x01
        ORIENTATION_ONLY = 0x02
        NONE = 0x03

    attributes = {
        0x0000: ("led_indicator_signals", LedIndicatorSignals, True),
        0x0001: ("unknown_attribute_1", t.enum8, True),
        0x0010: ("unknown_attribute_16", t.uint8_t, True),
        0x0011: ("unknown_attribute_17", t.uint16_t, True),
        0x0020: ("unknown_attribute_32", t.uint8_t, True),
        0x0021: ("unknown_attribute_33", t.uint16_t, True),
        0xFFFD: ("unknown_attribute_65533", t.uint16_t, True),
    }
